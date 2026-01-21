"""
Mami AI - Kullanıcı Analytics & Behavior Tracking
==================================================

Bu modül, kullanıcı davranışını ve etkileşimlerini takip eder.

Özellikler:
    - Event tracking (login, chat_start, message_sent, image_generated)
    - Batch collection (100 event veya 5 dakika)
    - Event flushing mekanizması
    - PII anonymization (gizlilik koruması)
    - SQLite veritabanına kaydetme

Kullanım:
    from app.core.analytics import get_analytics_tracker, track_event

    tracker = get_analytics_tracker()
    track_event("login", user_id=123)
    track_event("message_sent", user_id=123, data={"message_length": 50})
    
    # Batch'i manuel olarak flush et
    tracker.flush()

Event Türleri:
    - login: Kullanıcı giriş yaptı
    - chat_start: Sohbet başlatıldı
    - message_sent: Mesaj gönderildi
    - image_generated: Resim oluşturuldu

PII Anonymization:
    - Email adresleri hash'lenir
    - Telefon numaraları kaldırılır
    - Kişisel bilgiler anonymize edilir
"""

import asyncio
import hashlib
import json
import logging
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from sqlmodel import Session, select

from app.core.database import get_engine, get_session
from app.core.logger import get_logger

# =============================================================================
# YAPILANDIRMA SABİTLERİ
# =============================================================================

# Batch ayarları
BATCH_SIZE = 100  # Event sayısı
BATCH_TIMEOUT = 300  # 5 dakika (saniye)

# PII Patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

# Modül logger'ı
logger = get_logger(__name__)

# =============================================================================
# ANALYTICS EVENT MODEL
# =============================================================================


class AnalyticsEvent:
    """
    Analytics event'i temsil eden sınıf.
    
    Attributes:
        event_type: Event türü (login, chat_start, message_sent, image_generated)
        user_id: Kullanıcı ID'si
        timestamp: Event zamanı (ISO 8601)
        data: Event verisi (opsiyonel)
    """

    def __init__(
        self,
        event_type: str,
        user_id: int,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ):
        """
        Analytics event'i oluştur.
        
        Args:
            event_type: Event türü
            user_id: Kullanıcı ID'si
            data: Event verisi (opsiyonel)
            timestamp: Event zamanı (opsiyonel, varsayılan: şimdi)
        """
        self.event_type = event_type
        self.user_id = user_id
        self.data = data or {}
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Event'i dictionary'e dönüştür.
        
        Returns:
            Event dictionary'si
        """
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    def to_json(self) -> str:
        """
        Event'i JSON'a dönüştür.
        
        Returns:
            Event JSON'ı
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


# =============================================================================
# PII ANONYMIZATION
# =============================================================================


def anonymize_email(email: str) -> str:
    """
    Email adresini hash'le.
    
    Args:
        email: Email adresi
        
    Returns:
        Hash'lenmiş email (örn: "user@...com")
    """
    if not email or "@" not in email:
        return email

    # Email'i hash'le
    email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:8]
    
    # Maskelenmiş format: user@...com
    parts = email.split("@")
    domain = parts[1] if len(parts) > 1 else "example.com"
    
    return f"{email_hash}@{domain}"


def anonymize_text(text: str) -> str:
    """
    Metindeki PII verilerini anonymize et.
    
    Anonymize edilen veriler:
    - Email adresleri
    - Telefon numaraları
    - IP adresleri
    
    Args:
        text: Metin
        
    Returns:
        Anonymize edilmiş metin
    """
    if not isinstance(text, str):
        return text

    # Email'leri anonymize et
    text = EMAIL_PATTERN.sub("[EMAIL]", text)
    
    # Telefon numaralarını anonymize et
    text = PHONE_PATTERN.sub("[PHONE]", text)
    
    # IP adreslerini anonymize et
    text = IP_PATTERN.sub("[IP]", text)
    
    return text


def anonymize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Event verilerini anonymize et.
    
    Args:
        data: Event verisi
        
    Returns:
        Anonymize edilmiş event verisi
    """
    if not data:
        return data

    anonymized = {}
    
    for key, value in data.items():
        # Hassas alanları atla
        if key.lower() in ["password", "token", "secret", "api_key"]:
            anonymized[key] = "[REDACTED]"
        elif isinstance(value, str):
            # Metni anonymize et
            anonymized[key] = anonymize_text(value)
        elif isinstance(value, dict):
            # Nested dictionary'i recursively anonymize et
            anonymized[key] = anonymize_data(value)
        elif isinstance(value, list):
            # List'i anonymize et
            anonymized[key] = [
                anonymize_data(item) if isinstance(item, dict) else anonymize_text(str(item)) if isinstance(item, str) else item
                for item in value
            ]
        else:
            anonymized[key] = value
    
    return anonymized


# =============================================================================
# ANALYTICS TRACKER
# =============================================================================


class AnalyticsTracker:
    """
    Kullanıcı analytics'i takip eden sınıf.
    
    Özellikler:
    - Event batch collection
    - Otomatik flushing (timeout veya batch size)
    - PII anonymization
    - SQLite'a kaydetme
    """

    def __init__(self, batch_size: int = BATCH_SIZE, batch_timeout: int = BATCH_TIMEOUT):
        """
        Analytics tracker'ı oluştur.
        
        Args:
            batch_size: Batch boyutu (event sayısı)
            batch_timeout: Batch timeout (saniye)
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # Event buffer
        self.events: list[AnalyticsEvent] = []
        self.lock = threading.Lock()
        
        # Flush timer
        self.flush_timer: Optional[threading.Timer] = None
        self.last_flush_time = time.time()
        
        logger.info(f"[Analytics] Tracker başlatıldı (batch_size={batch_size}, timeout={batch_timeout}s)")

    def track_event(
        self,
        event_type: str,
        user_id: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Event'i track et.
        
        Args:
            event_type: Event türü
            user_id: Kullanıcı ID'si
            data: Event verisi (opsiyonel)
        """
        # Veriyi anonymize et
        anonymized_data = anonymize_data(data or {})
        
        # Event oluştur
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            data=anonymized_data,
        )
        
        with self.lock:
            self.events.append(event)
            logger.debug(f"[Analytics] Event tracked: {event_type} (user_id={user_id})")
            
            # Batch size'a ulaştıysa flush et
            if len(self.events) >= self.batch_size:
                self._flush_internal()
            else:
                # Timer'ı reset et
                self._reset_flush_timer()

    def _reset_flush_timer(self) -> None:
        """
        Flush timer'ı reset et.
        
        Timeout süresi içinde flush yapılmazsa otomatik flush et.
        """
        # Eski timer'ı iptal et
        if self.flush_timer:
            self.flush_timer.cancel()
        
        # Yeni timer oluştur
        self.flush_timer = threading.Timer(self.batch_timeout, self.flush)
        self.flush_timer.daemon = True
        self.flush_timer.start()

    def _flush_internal(self) -> None:
        """
        İç flush işlemi (lock'u varsayar).
        
        Bu fonksiyon lock'un içinde çağrılmalıdır.
        """
        if not self.events:
            return
        
        events_to_flush = self.events.copy()
        self.events.clear()
        
        # Timer'ı iptal et
        if self.flush_timer:
            self.flush_timer.cancel()
            self.flush_timer = None
        
        self.last_flush_time = time.time()
        
        # Lock'u serbest bırak ve flush et
        # (veritabanı işlemi uzun sürebilir)
        try:
            self._save_events(events_to_flush)
            logger.info(f"[Analytics] {len(events_to_flush)} event flush edildi")
        except Exception as e:
            logger.error(f"[Analytics] Flush hatası: {e}", exc_info=True)
            # Event'leri geri ekle (retry için)
            with self.lock:
                self.events.extend(events_to_flush)

    def flush(self) -> None:
        """
        Batch'i manuel olarak flush et.
        
        Tüm buffered event'leri veritabanına kaydet.
        """
        with self.lock:
            self._flush_internal()

    def _save_events(self, events: list[AnalyticsEvent]) -> None:
        """
        Event'leri veritabanına kaydet.
        
        Args:
            events: Kaydedilecek event'ler
        """
        if not events:
            return
        
        try:
            with get_session() as session:
                for event in events:
                    # Event'i JSON olarak kaydet
                    event_json = event.to_json()
                    
                    # SQL ile doğrudan insert (AnalyticsEvent tablosu henüz yok)
                    # Şimdilik log'a yazıyoruz, daha sonra tablo oluşturulacak
                    logger.debug(f"[Analytics] Event saved: {event_json}")
                    
                    # TODO: AnalyticsEvent tablosu oluşturulduktan sonra
                    # session.add(analytics_event)
                    # session.commit()
        except Exception as e:
            logger.error(f"[Analytics] Event kaydetme hatası: {e}", exc_info=True)
            raise

    def get_pending_events_count(self) -> int:
        """
        Pending event'lerin sayısını döndür.
        
        Returns:
            Pending event sayısı
        """
        with self.lock:
            return len(self.events)

    def shutdown(self) -> None:
        """
        Tracker'ı kapat ve pending event'leri flush et.
        
        Uygulama kapatılırken çağrılmalıdır.
        """
        logger.info("[Analytics] Tracker kapatılıyor...")
        
        # Timer'ı iptal et
        if self.flush_timer:
            self.flush_timer.cancel()
        
        # Pending event'leri flush et
        self.flush()
        
        logger.info("[Analytics] Tracker kapatıldı")


# =============================================================================
# GLOBAL TRACKER INSTANCE
# =============================================================================

_tracker: Optional[AnalyticsTracker] = None


def get_analytics_tracker() -> AnalyticsTracker:
    """
    Global analytics tracker'ı döndür (Singleton).
    
    Returns:
        AnalyticsTracker: Global tracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = AnalyticsTracker()
    return _tracker


def track_event(
    event_type: str,
    user_id: int,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Event'i track et (convenience function).
    
    Args:
        event_type: Event türü
        user_id: Kullanıcı ID'si
        data: Event verisi (opsiyonel)
    """
    tracker = get_analytics_tracker()
    tracker.track_event(event_type, user_id, data)


# =============================================================================
# EVENT TRACKING HELPER FUNCTIONS
# =============================================================================


def track_login(user_id: int) -> None:
    """
    Login event'ini track et.
    
    Args:
        user_id: Kullanıcı ID'si
    """
    track_event("login", user_id, {"timestamp": datetime.utcnow().isoformat()})


def track_chat_start(user_id: int, conversation_id: int) -> None:
    """
    Chat start event'ini track et.
    
    Args:
        user_id: Kullanıcı ID'si
        conversation_id: Sohbet ID'si
    """
    track_event("chat_start", user_id, {"conversation_id": conversation_id})


def track_message_sent(
    user_id: int,
    conversation_id: int,
    message_length: int,
    has_image: bool = False,
) -> None:
    """
    Message sent event'ini track et.
    
    Args:
        user_id: Kullanıcı ID'si
        conversation_id: Sohbet ID'si
        message_length: Mesaj uzunluğu
        has_image: Resim içeriyor mu
    """
    track_event(
        "message_sent",
        user_id,
        {
            "conversation_id": conversation_id,
            "message_length": message_length,
            "has_image": has_image,
        },
    )


def track_image_generated(
    user_id: int,
    conversation_id: int,
    model: str,
    prompt_length: int,
) -> None:
    """
    Image generated event'ini track et.
    
    Args:
        user_id: Kullanıcı ID'si
        conversation_id: Sohbet ID'si
        model: Resim modeli (flux, etc.)
        prompt_length: Prompt uzunluğu
    """
    track_event(
        "image_generated",
        user_id,
        {
            "conversation_id": conversation_id,
            "model": model,
            "prompt_length": prompt_length,
        },
    )
