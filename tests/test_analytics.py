"""
Mami AI - Analytics Modülü Unit Test'leri
==========================================

Bu test dosyası, analytics modülünün temel işlevselliğini test eder:
- Event tracking
- Batch collection
- PII anonymization
- Event flushing
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from app.core.analytics import (
    AnalyticsEvent,
    AnalyticsTracker,
    anonymize_email,
    anonymize_text,
    anonymize_data,
    track_event,
    track_login,
    track_chat_start,
    track_message_sent,
    track_image_generated,
    get_analytics_tracker,
)


# =============================================================================
# ANALYTICS EVENT TESTS
# =============================================================================


class TestAnalyticsEvent:
    """AnalyticsEvent sınıfı test'leri."""

    def test_event_creation(self):
        """Event oluşturma test'i."""
        event = AnalyticsEvent(
            event_type="login",
            user_id=123,
            data={"ip": "192.168.1.1"},
        )
        
        assert event.event_type == "login"
        assert event.user_id == 123
        assert event.data == {"ip": "192.168.1.1"}
        assert event.timestamp is not None

    def test_event_to_dict(self):
        """Event'i dictionary'e dönüştürme test'i."""
        event = AnalyticsEvent(
            event_type="login",
            user_id=123,
            data={"ip": "192.168.1.1"},
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "login"
        assert event_dict["user_id"] == 123
        assert event_dict["data"] == {"ip": "192.168.1.1"}
        assert "timestamp" in event_dict

    def test_event_to_json(self):
        """Event'i JSON'a dönüştürme test'i."""
        event = AnalyticsEvent(
            event_type="login",
            user_id=123,
            data={"ip": "192.168.1.1"},
        )
        
        event_json = event.to_json()
        
        assert isinstance(event_json, str)
        assert "login" in event_json
        assert "123" in event_json


# =============================================================================
# PII ANONYMIZATION TESTS
# =============================================================================


class TestPIIAnonymization:
    """PII anonymization test'leri."""

    def test_anonymize_email(self):
        """Email anonymization test'i."""
        email = "user@example.com"
        anonymized = anonymize_email(email)
        
        # Email hash'lenmiş olmalı
        assert "@" in anonymized
        assert "example.com" in anonymized
        assert "user" not in anonymized

    def test_anonymize_email_invalid(self):
        """Geçersiz email anonymization test'i."""
        email = "invalid-email"
        anonymized = anonymize_email(email)
        
        # Geçersiz email değişmemeli
        assert anonymized == email

    def test_anonymize_text_email(self):
        """Metindeki email anonymization test'i."""
        text = "Kullanıcı email: user@example.com"
        anonymized = anonymize_text(text)
        
        # Email [EMAIL] ile değiştirilmeli
        assert "[EMAIL]" in anonymized
        assert "user@example.com" not in anonymized

    def test_anonymize_text_phone(self):
        """Metindeki telefon anonymization test'i."""
        text = "Telefon: 555-123-4567"
        anonymized = anonymize_text(text)
        
        # Telefon [PHONE] ile değiştirilmeli
        assert "[PHONE]" in anonymized
        assert "555-123-4567" not in anonymized

    def test_anonymize_text_ip(self):
        """Metindeki IP anonymization test'i."""
        text = "IP adresi: 192.168.1.1"
        anonymized = anonymize_text(text)
        
        # IP [IP] ile değiştirilmeli
        assert "[IP]" in anonymized
        assert "192.168.1.1" not in anonymized

    def test_anonymize_data_password(self):
        """Şifre anonymization test'i."""
        data = {
            "username": "user",
            "password": "secret123",
            "api_key": "key123",
        }
        
        anonymized = anonymize_data(data)
        
        # Hassas alanlar [REDACTED] olmalı
        assert anonymized["password"] == "[REDACTED]"
        assert anonymized["api_key"] == "[REDACTED]"
        assert anonymized["username"] == "user"

    def test_anonymize_data_nested(self):
        """Nested data anonymization test'i."""
        data = {
            "user": {
                "email": "user@example.com",
                "name": "John",
            },
            "contact": {
                "phone": "555-123-4567",
            },
        }
        
        anonymized = anonymize_data(data)
        
        # Nested email anonymize edilmeli
        assert "[EMAIL]" in anonymized["user"]["email"]
        assert "[PHONE]" in anonymized["contact"]["phone"]
        assert anonymized["user"]["name"] == "John"

    def test_anonymize_data_list(self):
        """List data anonymization test'i."""
        data = {
            "emails": ["user1@example.com", "user2@example.com"],
        }
        
        anonymized = anonymize_data(data)
        
        # List'teki email'ler anonymize edilmeli
        assert all("[EMAIL]" in email for email in anonymized["emails"])


# =============================================================================
# ANALYTICS TRACKER TESTS
# =============================================================================


class TestAnalyticsTracker:
    """AnalyticsTracker sınıfı test'leri."""

    def test_tracker_creation(self):
        """Tracker oluşturma test'i."""
        tracker = AnalyticsTracker(batch_size=50, batch_timeout=60)
        
        assert tracker.batch_size == 50
        assert tracker.batch_timeout == 60
        assert len(tracker.events) == 0

    def test_track_event(self):
        """Event tracking test'i."""
        tracker = AnalyticsTracker(batch_size=100)
        
        tracker.track_event("login", user_id=123, data={"ip": "192.168.1.1"})
        
        assert len(tracker.events) == 1
        assert tracker.events[0].event_type == "login"
        assert tracker.events[0].user_id == 123

    def test_track_multiple_events(self):
        """Birden fazla event tracking test'i."""
        tracker = AnalyticsTracker(batch_size=100)
        
        for i in range(5):
            tracker.track_event("message_sent", user_id=123, data={"index": i})
        
        assert len(tracker.events) == 5

    def test_batch_flush_on_size(self):
        """Batch size'a ulaşınca flush test'i."""
        tracker = AnalyticsTracker(batch_size=3, batch_timeout=60)
        
        # 2 event ekle
        tracker.track_event("login", user_id=123)
        tracker.track_event("message_sent", user_id=123)
        assert len(tracker.events) == 2
        
        # 3. event ekle - flush olmalı
        with patch.object(tracker, '_save_events') as mock_save:
            tracker.track_event("image_generated", user_id=123)
            
            # Flush çağrılmalı
            mock_save.assert_called_once()
            assert len(tracker.events) == 0

    def test_pending_events_count(self):
        """Pending event sayısı test'i."""
        tracker = AnalyticsTracker(batch_size=100)
        
        tracker.track_event("login", user_id=123)
        tracker.track_event("message_sent", user_id=123)
        
        assert tracker.get_pending_events_count() == 2

    def test_manual_flush(self):
        """Manuel flush test'i."""
        tracker = AnalyticsTracker(batch_size=100)
        
        tracker.track_event("login", user_id=123)
        tracker.track_event("message_sent", user_id=123)
        
        with patch.object(tracker, '_save_events') as mock_save:
            tracker.flush()
            
            # Flush çağrılmalı
            mock_save.assert_called_once()
            assert len(tracker.events) == 0

    def test_anonymization_on_track(self):
        """Event tracking sırasında anonymization test'i."""
        tracker = AnalyticsTracker(batch_size=100)
        
        data = {
            "email": "user@example.com",
            "password": "secret123",
        }
        
        tracker.track_event("login", user_id=123, data=data)
        
        # Veri anonymize edilmeli
        assert "[EMAIL]" in tracker.events[0].data["email"]
        assert tracker.events[0].data["password"] == "[REDACTED]"

    def test_shutdown(self):
        """Tracker shutdown test'i."""
        tracker = AnalyticsTracker(batch_size=100)
        
        tracker.track_event("login", user_id=123)
        
        with patch.object(tracker, '_save_events') as mock_save:
            tracker.shutdown()
            
            # Flush çağrılmalı
            mock_save.assert_called_once()


# =============================================================================
# HELPER FUNCTIONS TESTS
# =============================================================================


class TestHelperFunctions:
    """Helper function'lar test'leri."""

    def test_track_login(self):
        """track_login helper test'i."""
        tracker = get_analytics_tracker()
        
        # Önceki event'leri temizle
        tracker.events.clear()
        
        track_login(user_id=123)
        
        assert len(tracker.events) == 1
        assert tracker.events[0].event_type == "login"
        assert tracker.events[0].user_id == 123

    def test_track_chat_start(self):
        """track_chat_start helper test'i."""
        tracker = get_analytics_tracker()
        
        # Önceki event'leri temizle
        tracker.events.clear()
        
        track_chat_start(user_id=123, conversation_id=456)
        
        assert len(tracker.events) == 1
        assert tracker.events[0].event_type == "chat_start"
        assert tracker.events[0].data["conversation_id"] == 456

    def test_track_message_sent(self):
        """track_message_sent helper test'i."""
        tracker = get_analytics_tracker()
        
        # Önceki event'leri temizle
        tracker.events.clear()
        
        track_message_sent(
            user_id=123,
            conversation_id=456,
            message_length=100,
            has_image=True,
        )
        
        assert len(tracker.events) == 1
        assert tracker.events[0].event_type == "message_sent"
        assert tracker.events[0].data["message_length"] == 100
        assert tracker.events[0].data["has_image"] is True

    def test_track_image_generated(self):
        """track_image_generated helper test'i."""
        tracker = get_analytics_tracker()
        
        # Önceki event'leri temizle
        tracker.events.clear()
        
        track_image_generated(
            user_id=123,
            conversation_id=456,
            model="flux",
            prompt_length=50,
        )
        
        assert len(tracker.events) == 1
        assert tracker.events[0].event_type == "image_generated"
        assert tracker.events[0].data["model"] == "flux"
        assert tracker.events[0].data["prompt_length"] == 50


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================


class TestAnalyticsProperties:
    """Analytics modülü için property-based test'ler."""

    def test_event_completeness_property(self):
        """
        Property 3: Event Completeness
        
        Tüm event'ler user_id, timestamp ve event_type içermeli.
        Farklı event türleri ve veri kombinasyonları için test et.
        
        Validates: Requirements 5.5
        
        Feature: logging-monitoring-system, Property 3: Event Completeness
        """
        tracker = AnalyticsTracker(batch_size=100)
        
        # Farklı event türleri ve veri kombinasyonları
        test_cases = [
            ("login", 123, {"ip": "192.168.1.1"}),
            ("chat_start", 456, {"conversation_id": 789}),
            ("message_sent", 789, {"message_length": 100, "has_image": True}),
            ("image_generated", 101, {"model": "flux", "prompt_length": 50}),
            ("login", 202, None),  # Veri olmadan
            ("message_sent", 303, {}),  # Boş veri
        ]
        
        for event_type, user_id, data in test_cases:
            tracker.track_event(event_type, user_id=user_id, data=data)
        
        # Tüm event'ler gerekli alanları içermeli
        assert len(tracker.events) == len(test_cases)
        
        for i, event in enumerate(tracker.events):
            # Gerekli alanlar kontrol et
            assert event.user_id is not None, f"Event {i}: user_id eksik"
            assert event.timestamp is not None, f"Event {i}: timestamp eksik"
            assert event.event_type is not None, f"Event {i}: event_type eksik"
            
            # Event türü doğru olmalı
            expected_type = test_cases[i][0]
            assert event.event_type == expected_type, f"Event {i}: event_type uyuşmuyor"
            
            # User ID doğru olmalı
            expected_user_id = test_cases[i][1]
            assert event.user_id == expected_user_id, f"Event {i}: user_id uyuşmuyor"
            
            # Timestamp ISO 8601 formatında olmalı
            assert "T" in event.timestamp, f"Event {i}: timestamp format yanlış"
            
            # Data dictionary olmalı
            assert isinstance(event.data, dict), f"Event {i}: data dict değil"

    def test_batch_collection_property(self):
        """
        Property 3: Event Completeness (Batch Collection)
        
        Batch collection sırasında hiçbir event kaybolmamalı.
        
        Validates: Requirements 5.5
        
        Feature: logging-monitoring-system, Property 3: Event Completeness
        """
        tracker = AnalyticsTracker(batch_size=5, batch_timeout=60)
        
        # _save_events'i mock et (flush'ı kontrol etmek için)
        with patch.object(tracker, '_save_events') as mock_save:
            # 10 event ekle (batch size'ı aşacak)
            for i in range(10):
                tracker.track_event(
                    "message_sent",
                    user_id=100 + i,
                    data={"index": i, "message": f"Message {i}"},
                )
            
            # 5. event'te flush tetiklenmeli (batch_size=5)
            # 10. event'te tekrar flush tetiklenmeli
            assert mock_save.call_count == 2, f"Expected 2 flushes, got {mock_save.call_count}"
            
            # Her flush'ta 5 event gönderilmeli
            for call in mock_save.call_args_list:
                flushed_events = call[0][0]
                assert len(flushed_events) == 5, f"Expected 5 events, got {len(flushed_events)}"
            
            # Buffer temiz olmalı
            assert len(tracker.events) == 0

    def test_anonymization_property(self):
        """
        Property 8: Analytics Anonymization
        
        Tüm PII veriler anonymize edilmeli.
        Farklı PII türleri ve kombinasyonları test et.
        
        Validates: Requirements 5.8
        
        Feature: logging-monitoring-system, Property 8: Analytics Anonymization
        """
        tracker = AnalyticsTracker(batch_size=100)
        
        # Farklı PII kombinasyonları
        test_cases = [
            {
                "email": "user@example.com",
                "phone": "555-123-4567",
                "ip": "192.168.1.1",
                "password": "secret123",
            },
            {
                "api_key": "sk-1234567890",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                "secret": "my-secret-key",
            },
            {
                "nested": {
                    "email": "nested@example.com",
                    "password": "nested-secret",
                },
                "list": ["user1@example.com", "user2@example.com"],
            },
        ]
        
        for i, data in enumerate(test_cases):
            tracker.track_event("login", user_id=100 + i, data=data)
        
        # Tüm event'ler anonymize edilmeli
        assert len(tracker.events) == len(test_cases)
        
        for i, event in enumerate(tracker.events):
            anonymized_data = event.data
            
            # Test case 1: Temel PII
            if i == 0:
                # Email anonymize edilmeli
                assert "[EMAIL]" in anonymized_data["email"], "Email anonymize edilmedi"
                assert "user@example.com" not in anonymized_data["email"], "Email orijinal değeri kaldı"
                
                # Telefon anonymize edilmeli
                assert "[PHONE]" in anonymized_data["phone"], "Telefon anonymize edilmedi"
                assert "555-123-4567" not in anonymized_data["phone"], "Telefon orijinal değeri kaldı"
                
                # IP anonymize edilmeli
                assert "[IP]" in anonymized_data["ip"], "IP anonymize edilmedi"
                assert "192.168.1.1" not in anonymized_data["ip"], "IP orijinal değeri kaldı"
                
                # Şifre redacted olmalı
                assert anonymized_data["password"] == "[REDACTED]", "Şifre redacted değil"
            
            # Test case 2: Hassas alanlar
            elif i == 1:
                assert anonymized_data["api_key"] == "[REDACTED]", "API key redacted değil"
                assert anonymized_data["token"] == "[REDACTED]", "Token redacted değil"
                assert anonymized_data["secret"] == "[REDACTED]", "Secret redacted değil"
            
            # Test case 3: Nested ve list
            elif i == 2:
                # Nested email anonymize edilmeli
                assert "[EMAIL]" in anonymized_data["nested"]["email"], "Nested email anonymize edilmedi"
                assert anonymized_data["nested"]["password"] == "[REDACTED]", "Nested password redacted değil"
                
                # List'teki email'ler anonymize edilmeli
                assert all("[EMAIL]" in email for email in anonymized_data["list"]), "List email'leri anonymize edilmedi"

    def test_anonymization_idempotence_property(self):
        """
        Property 8: Analytics Anonymization (Idempotence)
        
        Anonymization iki kez uygulanırsa aynı sonuç verilmeli.
        
        Validates: Requirements 5.8
        
        Feature: logging-monitoring-system, Property 8: Analytics Anonymization
        """
        # Orijinal veri
        original_data = {
            "email": "user@example.com",
            "phone": "555-123-4567",
            "message": "Contact me at user@example.com",
        }
        
        # İlk anonymization
        anonymized_once = anonymize_data(original_data)
        
        # İkinci anonymization
        anonymized_twice = anonymize_data(anonymized_once)
        
        # Sonuçlar aynı olmalı (idempotent)
        assert anonymized_once == anonymized_twice, "Anonymization idempotent değil"
        
        # Orijinal veri değişmemeli
        assert original_data["email"] == "user@example.com", "Orijinal veri değişti"

    def test_event_tracking_consistency_property(self):
        """
        Property 3: Event Completeness (Consistency)
        
        Event tracking sırasında veri tutarlılığı korunmalı.
        
        Validates: Requirements 5.5
        
        Feature: logging-monitoring-system, Property 3: Event Completeness
        """
        tracker = AnalyticsTracker(batch_size=100)
        
        # Aynı user_id ile birden fazla event ekle
        user_id = 123
        event_count = 10
        
        for i in range(event_count):
            tracker.track_event(
                "message_sent",
                user_id=user_id,
                data={"sequence": i},
            )
        
        # Tüm event'ler aynı user_id'ye sahip olmalı
        assert len(tracker.events) == event_count
        assert all(event.user_id == user_id for event in tracker.events), "User ID tutarlı değil"
        
        # Sequence numaraları doğru olmalı
        for i, event in enumerate(tracker.events):
            assert event.data["sequence"] == i, f"Sequence {i} uyuşmuyor"
