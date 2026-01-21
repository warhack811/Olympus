"""
Mami AI - Alert & Notification Sistemi
========================================

Bu modül, sistem metriklerini izler ve kritik durumlarda alert'ler gönderir.

Özellikler:
    - Alert kurallarını tanımla (error rate, response time, disk space, memory)
    - Email notification'ı ekle
    - Slack notification'ı ekle
    - Alert history'sini kaydet
    - Alert escalation mekanizması ekle (ilk alert'e cevap yoksa)

Kullanım:
    from app.core.alerting import (
        AlertManager,
        get_alert_manager,
        send_alert,
    )

    # Alert manager'ı başlat
    manager = get_alert_manager()
    await manager.start()
    
    # Alert gönder
    await send_alert(
        alert_type="error_rate",
        severity="critical",
        message="Error rate %5'i aşıyor",
        data={"error_rate": 6.5, "threshold": 5.0}
    )

Alert Türleri:
    - error_rate: Hata oranı threshold'unu aştı
    - response_time: Response time threshold'unu aştı
    - disk_space: Disk alanı threshold'unu aştı
    - memory_usage: Memory kullanımı threshold'unu aştı
    - endpoint_down: API endpoint'i down oldu
"""

import asyncio
import aiosmtplib
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

from app.core.logger import get_logger, log_event
from app.core.database import get_session
from app.core.models import AlertHistory

# =============================================================================
# YAPILANDIRMA SABİTLERİ
# =============================================================================

# Alert cooldown (aynı alert'i tekrar göndermeden önce bekleme süresi)
ALERT_COOLDOWN_SECONDS = 300  # 5 dakika

# Alert escalation timeout (ilk alert'e cevap yoksa escalate et)
ALERT_ESCALATION_TIMEOUT_SECONDS = 1800  # 30 dakika

# Alert history retention (kaç gün tutulacak)
ALERT_HISTORY_RETENTION_DAYS = 90

# =============================================================================
# ENUM'LAR
# =============================================================================


class AlertSeverity(str, Enum):
    """Alert severity seviyeleri."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Alert türleri."""
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    DISK_SPACE = "disk_space"
    MEMORY_USAGE = "memory_usage"
    ENDPOINT_DOWN = "endpoint_down"
    CUSTOM = "custom"


class NotificationChannel(str, Enum):
    """Notification kanalları."""
    EMAIL = "email"
    SLACK = "slack"
    LOG = "log"


# =============================================================================
# VERİ YAPILARI
# =============================================================================


@dataclass
class Alert:
    """Alert nesnesi."""
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    data: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: Optional[str] = None
    
    def __hash__(self):
        """Alert'i hash'le (set'te kullanmak için)."""
        return hash((self.alert_type, self.severity, self.message))
    
    def __eq__(self, other):
        """Alert'leri karşılaştır."""
        if not isinstance(other, Alert):
            return False
        return (
            self.alert_type == other.alert_type
            and self.severity == other.severity
            and self.message == other.message
        )


@dataclass
class AlertState:
    """Alert durumu (escalation için)."""
    alert: Alert
    first_triggered_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered_at: datetime = field(default_factory=datetime.utcnow)
    trigger_count: int = 1
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def should_escalate(self) -> bool:
        """Alert'in escalate edilmesi gerekip gerekmediğini kontrol et."""
        if self.escalated or self.acknowledged:
            return False
        
        # Escalation timeout'unu kontrol et
        elapsed = datetime.utcnow() - self.first_triggered_at
        return elapsed.total_seconds() > ALERT_ESCALATION_TIMEOUT_SECONDS
    
    def should_send_notification(self) -> bool:
        """Notification gönderilmesi gerekip gerekmediğini kontrol et."""
        if self.acknowledged:
            return False
        
        # Cooldown'ı kontrol et
        elapsed = datetime.utcnow() - self.last_triggered_at
        return elapsed.total_seconds() > ALERT_COOLDOWN_SECONDS


# =============================================================================
# NOTIFICATION HANDLERS
# =============================================================================


class NotificationHandler:
    """Notification gönderimi için base class."""
    
    def __init__(self):
        """Handler'ı başlat."""
        self.logger = get_logger(__name__)
    
    async def send(self, alert: Alert) -> bool:
        """
        Alert'i gönder.
        
        Args:
            alert: Gönderilecek alert
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        raise NotImplementedError


class EmailNotificationHandler(NotificationHandler):
    """Email notification handler."""
    
    async def send(self, alert: Alert) -> bool:
        """
        Alert'i email ile gönder.
        
        Args:
            alert: Gönderilecek alert
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        try:
            # Environment variables'ı al
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            alert_email_to = os.getenv("ALERT_EMAIL_TO")
            
            # Konfigürasyon kontrol et
            if not all([smtp_server, smtp_username, smtp_password, alert_email_to]):
                self.logger.warning("Email konfigürasyonu eksik, email gönderilemedi")
                return False
            
            # Email içeriğini oluştur
            subject = f"[{alert.severity.upper()}] {alert.alert_type.value}: {alert.message}"
            body = self._format_email_body(alert)
            
            # Email gönder
            async with aiosmtplib.SMTP(hostname=smtp_server, port=smtp_port) as smtp:
                await smtp.login(smtp_username, smtp_password)
                await smtp.sendmail(
                    sender=smtp_username,
                    recipients=[alert_email_to],
                    message=f"Subject: {subject}\n\n{body}"
                )
            
            self.logger.info(f"Email alert gönderildi: {alert.alert_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Email alert gönderilemedi: {e}", exc_info=True)
            return False
    
    def _format_email_body(self, alert: Alert) -> str:
        """Email gövdesini formatla."""
        body = f"""
Alert Detayları
===============

Tür: {alert.alert_type.value}
Severity: {alert.severity.value}
Zaman: {alert.timestamp.isoformat()}

Mesaj:
{alert.message}

Veri:
{json.dumps(alert.data, indent=2, ensure_ascii=False)}

---
Bu email otomatik olarak gönderilmiştir.
"""
        return body


class SlackNotificationHandler(NotificationHandler):
    """Slack notification handler."""
    
    async def send(self, alert: Alert) -> bool:
        """
        Alert'i Slack'e gönder.
        
        Args:
            alert: Gönderilecek alert
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        try:
            # Webhook URL'sini al
            webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            
            if not webhook_url:
                self.logger.warning("Slack webhook URL'si eksik, Slack mesajı gönderilemedi")
                return False
            
            # Slack mesajını oluştur
            payload = self._format_slack_message(alert)
            
            # Slack'e gönder
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 200:
                        self.logger.error(f"Slack API hatası: {response.status}")
                        return False
            
            self.logger.info(f"Slack alert gönderildi: {alert.alert_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Slack alert gönderilemedi: {e}", exc_info=True)
            return False
    
    def _format_slack_message(self, alert: Alert) -> Dict:
        """Slack mesajını formatla."""
        # Severity'ye göre renk seç
        color_map = {
            AlertSeverity.INFO: "#36a64f",      # Yeşil
            AlertSeverity.WARNING: "#ff9900",   # Turuncu
            AlertSeverity.CRITICAL: "#ff0000",  # Kırmızı
        }
        color = color_map.get(alert.severity, "#808080")
        
        # Slack mesajını oluştur
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{alert.alert_type.value.upper()} - {alert.severity.value.upper()}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Zaman",
                            "value": alert.timestamp.isoformat(),
                            "short": True
                        },
                        {
                            "title": "Veri",
                            "value": f"```{json.dumps(alert.data, indent=2, ensure_ascii=False)}```",
                            "short": False
                        }
                    ],
                    "footer": "Mami AI Alert System",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        return payload


class LogNotificationHandler(NotificationHandler):
    """Log notification handler."""
    
    async def send(self, alert: Alert) -> bool:
        """
        Alert'i log'a yaz.
        
        Args:
            alert: Gönderilecek alert
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        try:
            # Alert'i log'la
            log_event(
                self.logger,
                event_type="alert",
                event_name=alert.alert_type.value,
                data={
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "data": alert.data,
                    "timestamp": alert.timestamp.isoformat(),
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Log alert yazılamadı: {e}", exc_info=True)
            return False


# =============================================================================
# ALERT MANAGER
# =============================================================================


class AlertManager:
    """
    Alert ve notification sistemi.
    
    Özellikler:
    - Alert kurallarını tanımla
    - Alert'leri tetikle
    - Notification'ları gönder (email, Slack, log)
    - Alert history'sini kaydet
    - Alert escalation mekanizması
    """
    
    def __init__(self):
        """Alert manager'ı başlat."""
        self.logger = get_logger(__name__)
        
        # Alert state tracking
        self.alert_states: Dict[str, AlertState] = {}
        
        # Notification handlers
        self.handlers: Dict[NotificationChannel, NotificationHandler] = {
            NotificationChannel.EMAIL: EmailNotificationHandler(),
            NotificationChannel.SLACK: SlackNotificationHandler(),
            NotificationChannel.LOG: LogNotificationHandler(),
        }
        
        # Background task
        self.cleanup_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Alert manager'ı başlat."""
        if self.running:
            self.logger.warning("Alert manager zaten çalışıyor")
            return
        
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("Alert manager başlatıldı")
    
    async def stop(self) -> None:
        """Alert manager'ı durdur."""
        if not self.running:
            return
        
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Alert manager durduruldu")
    
    async def _cleanup_loop(self) -> None:
        """
        Background cleanup loop'u.
        
        Her 1 saatte bir:
        1. Eski alert'leri temizle
        2. Escalation'ları kontrol et
        """
        while self.running:
            try:
                await asyncio.sleep(3600)  # 1 saat
                
                if not self.running:
                    break
                
                # Cleanup'ı çalıştır
                await self._perform_cleanup()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Alert cleanup loop'unda hata: {e}",
                    exc_info=True
                )
    
    async def _perform_cleanup(self) -> None:
        """
        Cleanup'ı çalıştır.
        
        1. Eski alert'leri temizle
        2. Escalation'ları kontrol et
        """
        async with self._lock:
            # Eski alert'leri temizle (24 saat)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            for alert_key in list(self.alert_states.keys()):
                state = self.alert_states[alert_key]
                
                # Acknowledged ve eski alert'leri sil
                if state.acknowledged and state.acknowledged_at < cutoff_time:
                    del self.alert_states[alert_key]
            
            # Escalation'ları kontrol et
            for alert_key, state in self.alert_states.items():
                if state.should_escalate():
                    await self._escalate_alert(state)
    
    async def _escalate_alert(self, state: AlertState) -> None:
        """
        Alert'i escalate et.
        
        Args:
            state: Alert state
        """
        try:
            state.escalated = True
            state.escalated_at = datetime.utcnow()
            
            # Escalation mesajı oluştur
            escalation_alert = Alert(
                alert_type=state.alert.alert_type,
                severity=AlertSeverity.CRITICAL,
                message=f"ESCALATION: {state.alert.message} (İlk alert'e cevap yoksa escalate edildi)",
                data={
                    **state.alert.data,
                    "escalation_reason": "no_response",
                    "first_triggered_at": state.first_triggered_at.isoformat(),
                    "trigger_count": state.trigger_count,
                }
            )
            
            # Escalation alert'ini gönder
            await self._send_notifications(escalation_alert)
            
            self.logger.warning(f"Alert escalate edildi: {state.alert.alert_type.value}")
            
        except Exception as e:
            self.logger.error(f"Alert escalation başarısız: {e}", exc_info=True)
    
    async def trigger_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        data: Optional[Dict] = None,
    ) -> None:
        """
        Alert'i tetikle.
        
        Args:
            alert_type: Alert türü
            severity: Alert severity'si
            message: Alert mesajı
            data: Alert verisi
        """
        try:
            # Alert nesnesi oluştur
            alert = Alert(
                alert_type=alert_type,
                severity=severity,
                message=message,
                data=data or {},
            )
            
            async with self._lock:
                # Alert key'ini oluştur
                alert_key = f"{alert_type.value}:{message}"
                
                # Alert state'ini kontrol et
                if alert_key in self.alert_states:
                    state = self.alert_states[alert_key]
                    state.last_triggered_at = datetime.utcnow()
                    state.trigger_count += 1
                    
                    # Notification gönderilmesi gerekip gerekmediğini kontrol et
                    if not state.should_send_notification():
                        self.logger.debug(f"Alert cooldown'da: {alert_key}")
                        return
                else:
                    # Yeni alert state'i oluştur
                    state = AlertState(alert=alert)
                    self.alert_states[alert_key] = state
                
                # Notification'ları gönder
                await self._send_notifications(alert)
                
                # Alert history'ye kaydet
                await self._save_alert_history(alert)
                
        except Exception as e:
            self.logger.error(f"Alert tetiklenemedi: {e}", exc_info=True)
    
    async def _send_notifications(self, alert: Alert) -> None:
        """
        Notification'ları gönder.
        
        Args:
            alert: Gönderilecek alert
        """
        # Severity'ye göre hangi kanalları kullanacağını belirle
        channels = self._get_notification_channels(alert.severity)
        
        # Notification'ları gönder
        tasks = [
            self.handlers[channel].send(alert)
            for channel in channels
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sonuçları log'la
        for channel, result in zip(channels, results):
            if isinstance(result, Exception):
                self.logger.error(f"{channel.value} notification hatası: {result}")
            elif result:
                self.logger.debug(f"{channel.value} notification gönderildi")
    
    def _get_notification_channels(self, severity: AlertSeverity) -> List[NotificationChannel]:
        """
        Severity'ye göre notification kanallarını belirle.
        
        Args:
            severity: Alert severity'si
            
        Returns:
            List[NotificationChannel]: Kullanılacak kanallar
        """
        # Her zaman log'a yaz
        channels = [NotificationChannel.LOG]
        
        # Severity'ye göre diğer kanalları ekle
        if severity == AlertSeverity.WARNING:
            channels.append(NotificationChannel.SLACK)
        elif severity == AlertSeverity.CRITICAL:
            channels.extend([NotificationChannel.EMAIL, NotificationChannel.SLACK])
        
        return channels
    
    async def _save_alert_history(self, alert: Alert) -> None:
        """
        Alert history'ye kaydet.
        
        Args:
            alert: Kaydedilecek alert
        """
        try:
            # Database session'ı al
            with get_session() as session:
                # Alert history nesnesi oluştur
                history = AlertHistory(
                    alert_type=alert.alert_type.value,
                    severity=alert.severity.value,
                    message=alert.message,
                    data=alert.data,
                    created_at=alert.timestamp,
                )
                
                # Database'e kaydet
                session.add(history)
                session.commit()
                
        except Exception as e:
            self.logger.error(f"Alert history kaydedilemedi: {e}", exc_info=True)
    
    def acknowledge_alert(
        self,
        alert_type: AlertType,
        message: str,
        acknowledged_by: str,
    ) -> bool:
        """
        Alert'i acknowledge et.
        
        Args:
            alert_type: Alert türü
            message: Alert mesajı
            acknowledged_by: Acknowledge eden kişi
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        try:
            # Alert key'ini oluştur
            alert_key = f"{alert_type.value}:{message}"
            
            # Alert state'ini bul
            if alert_key not in self.alert_states:
                self.logger.warning(f"Alert bulunamadı: {alert_key}")
                return False
            
            # Alert'i acknowledge et
            state = self.alert_states[alert_key]
            state.acknowledged = True
            state.acknowledged_at = datetime.utcnow()
            state.acknowledged_by = acknowledged_by
            
            self.logger.info(f"Alert acknowledge edildi: {alert_key} by {acknowledged_by}")
            return True
            
        except Exception as e:
            self.logger.error(f"Alert acknowledge edilemedi: {e}", exc_info=True)
            return False
    
    def get_active_alerts(self) -> List[AlertState]:
        """
        Aktif alert'leri al.
        
        Returns:
            List[AlertState]: Aktif alert'ler
        """
        return [
            state for state in self.alert_states.values()
            if not state.acknowledged
        ]
    
    def get_alert_state(self, alert_type: AlertType, message: str) -> Optional[AlertState]:
        """
        Alert state'ini al.
        
        Args:
            alert_type: Alert türü
            message: Alert mesajı
            
        Returns:
            AlertState veya None
        """
        alert_key = f"{alert_type.value}:{message}"
        return self.alert_states.get(alert_key)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """
    Global alert manager instance'ını al.
    
    Returns:
        AlertManager: Global instance
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


async def start_alert_manager() -> None:
    """Alert manager'ı başlat."""
    manager = get_alert_manager()
    await manager.start()


async def stop_alert_manager() -> None:
    """Alert manager'ı durdur."""
    manager = get_alert_manager()
    await manager.stop()


async def send_alert(
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
    data: Optional[Dict] = None,
) -> None:
    """
    Alert gönder.
    
    Args:
        alert_type: Alert türü
        severity: Alert severity'si
        message: Alert mesajı
        data: Alert verisi
    """
    manager = get_alert_manager()
    await manager.trigger_alert(alert_type, severity, message, data)


def acknowledge_alert(
    alert_type: AlertType,
    message: str,
    acknowledged_by: str,
) -> bool:
    """
    Alert'i acknowledge et.
    
    Args:
        alert_type: Alert türü
        message: Alert mesajı
        acknowledged_by: Acknowledge eden kişi
        
    Returns:
        bool: Başarılı olup olmadığı
    """
    manager = get_alert_manager()
    return manager.acknowledge_alert(alert_type, message, acknowledged_by)


def get_active_alerts() -> List[AlertState]:
    """
    Aktif alert'leri al.
    
    Returns:
        List[AlertState]: Aktif alert'ler
    """
    manager = get_alert_manager()
    return manager.get_active_alerts()
