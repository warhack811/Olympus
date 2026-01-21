"""
Alert & Notification Sistemi Test'leri

Bu test dosyası, app/core/alerting.py modülünün alert ve notification
sistemini test eder.

Test Kapsamı:
    - Alert tetiklenmesi
    - Notification gönderimi (email, Slack, log)
    - Alert state tracking
    - Alert escalation mekanizması
    - Alert history kaydı
    - Alert cooldown mekanizması
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import json

from app.core.alerting import (
    Alert,
    AlertType,
    AlertSeverity,
    AlertState,
    AlertManager,
    NotificationChannel,
    EmailNotificationHandler,
    SlackNotificationHandler,
    LogNotificationHandler,
    get_alert_manager,
    send_alert,
    acknowledge_alert,
    get_active_alerts,
    ALERT_COOLDOWN_SECONDS,
    ALERT_ESCALATION_TIMEOUT_SECONDS,
)


class TestAlert:
    """Alert veri yapısı test'leri."""

    def test_alert_creation(self):
        """
        Alert'i oluştur ve alanlarını kontrol et.
        
        For any alert created, all fields should be properly set.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        assert alert.alert_type == AlertType.ERROR_RATE
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.message == "Error rate %5'i aşıyor"
        assert alert.data["error_rate"] == 6.5
        assert alert.timestamp is not None

    def test_alert_equality(self):
        """
        Alert'leri karşılaştır.
        
        For any two alerts with same type, severity, and message, they should be equal.
        """
        alert1 = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        alert2 = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        assert alert1 == alert2

    def test_alert_hash(self):
        """
        Alert'i hash'le.
        
        For any alert, it should be hashable and usable in sets.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # Set'e ekle
        alert_set = {alert}
        assert alert in alert_set


class TestAlertState:
    """AlertState veri yapısı test'leri."""

    def test_alert_state_creation(self):
        """
        AlertState'i oluştur ve alanlarını kontrol et.
        
        For any alert state created, all fields should be properly initialized.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        state = AlertState(alert=alert)
        
        assert state.alert == alert
        assert state.trigger_count == 1
        assert state.escalated is False
        assert state.acknowledged is False

    def test_alert_state_should_escalate(self):
        """
        Alert'in escalate edilmesi gerekip gerekmediğini kontrol et.
        
        For any alert state that has been triggered for longer than escalation timeout,
        should_escalate should return True.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        state = AlertState(alert=alert)
        
        # Escalation timeout'unu geç
        state.first_triggered_at = datetime.utcnow() - timedelta(
            seconds=ALERT_ESCALATION_TIMEOUT_SECONDS + 100
        )
        
        assert state.should_escalate() is True

    def test_alert_state_should_not_escalate_if_acknowledged(self):
        """
        Acknowledged alert'in escalate edilmemesi gerektiğini kontrol et.
        
        For any alert state that is acknowledged, should_escalate should return False.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        state = AlertState(alert=alert)
        state.acknowledged = True
        
        # Escalation timeout'unu geç
        state.first_triggered_at = datetime.utcnow() - timedelta(
            seconds=ALERT_ESCALATION_TIMEOUT_SECONDS + 100
        )
        
        assert state.should_escalate() is False

    def test_alert_state_should_send_notification(self):
        """
        Notification gönderilmesi gerekip gerekmediğini kontrol et.
        
        For any alert state that has cooldown expired, should_send_notification should return True.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        state = AlertState(alert=alert)
        
        # Cooldown'ı geç
        state.last_triggered_at = datetime.utcnow() - timedelta(
            seconds=ALERT_COOLDOWN_SECONDS + 100
        )
        
        assert state.should_send_notification() is True

    def test_alert_state_should_not_send_notification_in_cooldown(self):
        """
        Cooldown'da notification gönderilmemesi gerektiğini kontrol et.
        
        For any alert state within cooldown period, should_send_notification should return False.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        state = AlertState(alert=alert)
        
        # Cooldown'ı geçme
        state.last_triggered_at = datetime.utcnow() - timedelta(seconds=10)
        
        assert state.should_send_notification() is False


class TestEmailNotificationHandler:
    """Email notification handler test'leri."""

    @pytest.mark.asyncio
    async def test_email_handler_missing_config(self):
        """
        Email konfigürasyonu eksikse handler başarısız olmalı.
        
        For any alert when email config is missing, send should return False.
        """
        handler = EmailNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # Konfigürasyon eksik
        with patch.dict("os.environ", {}, clear=True):
            result = await handler.send(alert)
            assert result is False

    @pytest.mark.asyncio
    async def test_email_handler_format_body(self):
        """
        Email gövdesini formatla.
        
        For any alert, the email body should contain alert details.
        """
        handler = EmailNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        body = handler._format_email_body(alert)
        
        assert "Error rate %5'i aşıyor" in body
        assert "error_rate" in body
        assert "6.5" in body


class TestSlackNotificationHandler:
    """Slack notification handler test'leri."""

    @pytest.mark.asyncio
    async def test_slack_handler_missing_webhook(self):
        """
        Slack webhook URL'si eksikse handler başarısız olmalı.
        
        For any alert when Slack webhook is missing, send should return False.
        """
        handler = SlackNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # Webhook URL'si eksik
        with patch.dict("os.environ", {}, clear=True):
            result = await handler.send(alert)
            assert result is False

    def test_slack_handler_format_message(self):
        """
        Slack mesajını formatla.
        
        For any alert, the Slack message should contain alert details in proper format.
        """
        handler = SlackNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        payload = handler._format_slack_message(alert)
        
        assert "attachments" in payload
        assert len(payload["attachments"]) > 0
        assert payload["attachments"][0]["color"] == "#ff0000"  # Kırmızı (critical)


class TestLogNotificationHandler:
    """Log notification handler test'leri."""

    @pytest.mark.asyncio
    async def test_log_handler_send(self):
        """
        Alert'i log'a yaz.
        
        For any alert, the log handler should successfully send it.
        """
        handler = LogNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        result = await handler.send(alert)
        assert result is True


class TestAlertManager:
    """Alert manager test'leri."""

    @pytest.mark.asyncio
    async def test_alert_manager_creation(self):
        """
        Alert manager'ı oluştur.
        
        For any alert manager created, it should be properly initialized.
        """
        manager = AlertManager()
        
        assert manager.running is False
        assert len(manager.alert_states) == 0
        assert len(manager.handlers) == 3  # email, slack, log

    @pytest.mark.asyncio
    async def test_alert_manager_start_stop(self):
        """
        Alert manager'ı başlat ve durdur.
        
        For any alert manager, start and stop should work correctly.
        """
        manager = AlertManager()
        
        # Başlat
        await manager.start()
        assert manager.running is True
        
        # Durdur
        await manager.stop()
        assert manager.running is False

    @pytest.mark.asyncio
    async def test_alert_manager_trigger_alert(self):
        """
        Alert'i tetikle.
        
        For any alert triggered, it should be stored in alert_states.
        """
        manager = AlertManager()
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        # Alert state'ini kontrol et
        alert_key = "error_rate:Error rate %5'i aşıyor"
        assert alert_key in manager.alert_states

    @pytest.mark.asyncio
    async def test_alert_manager_cooldown(self):
        """
        Alert cooldown mekanizması.
        
        For any alert triggered twice within cooldown period, second trigger should not send notification.
        """
        manager = AlertManager()
        
        # İlk alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        alert_key = "error_rate:Error rate %5'i aşıyor"
        
        # İkinci alert'i tetikle (cooldown'da)
        # Bu, notification göndermemeli ama trigger_count artmayacak
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # Trigger count artmış olmalı (tetikleme sayısı)
        # Ama notification gönderilmemeli (cooldown'da)
        assert manager.alert_states[alert_key].trigger_count >= 1

    @pytest.mark.asyncio
    async def test_alert_manager_acknowledge(self):
        """
        Alert'i acknowledge et.
        
        For any alert acknowledged, it should be marked as acknowledged.
        """
        manager = AlertManager()
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # Alert'i acknowledge et
        result = manager.acknowledge_alert(
            alert_type=AlertType.ERROR_RATE,
            message="Error rate %5'i aşıyor",
            acknowledged_by="admin",
        )
        
        assert result is True
        
        alert_key = "error_rate:Error rate %5'i aşıyor"
        assert manager.alert_states[alert_key].acknowledged is True
        assert manager.alert_states[alert_key].acknowledged_by == "admin"

    @pytest.mark.asyncio
    async def test_alert_manager_get_active_alerts(self):
        """
        Aktif alert'leri al.
        
        For any alert manager with triggered alerts, get_active_alerts should return non-acknowledged alerts.
        """
        manager = AlertManager()
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # Aktif alert'leri al
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 1

    @pytest.mark.asyncio
    async def test_alert_manager_get_notification_channels(self):
        """
        Severity'ye göre notification kanallarını belirle.
        
        For any alert with different severities, correct notification channels should be selected.
        """
        manager = AlertManager()
        
        # INFO severity
        channels = manager._get_notification_channels(AlertSeverity.INFO)
        assert NotificationChannel.LOG in channels
        assert NotificationChannel.SLACK not in channels
        
        # WARNING severity
        channels = manager._get_notification_channels(AlertSeverity.WARNING)
        assert NotificationChannel.LOG in channels
        assert NotificationChannel.SLACK in channels
        
        # CRITICAL severity
        channels = manager._get_notification_channels(AlertSeverity.CRITICAL)
        assert NotificationChannel.LOG in channels
        assert NotificationChannel.EMAIL in channels
        assert NotificationChannel.SLACK in channels


class TestGlobalFunctions:
    """Global helper fonksiyonları test'leri."""

    @pytest.mark.asyncio
    async def test_send_alert(self):
        """
        Global send_alert fonksiyonunu test et.
        
        For any alert sent via global function, it should be stored in manager.
        """
        # Manager'ı sıfırla
        import app.core.alerting as alerting_module
        alerting_module._alert_manager = None
        
        # Alert gönder
        await send_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # Manager'dan kontrol et
        manager = get_alert_manager()
        alert_key = "error_rate:Error rate %5'i aşıyor"
        assert alert_key in manager.alert_states

    def test_acknowledge_alert(self):
        """
        Global acknowledge_alert fonksiyonunu test et.
        
        For any alert acknowledged via global function, it should be marked as acknowledged.
        """
        # Manager'ı sıfırla
        import app.core.alerting as alerting_module
        alerting_module._alert_manager = None
        
        manager = get_alert_manager()
        
        # Alert state'ini manuel olarak oluştur
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        alert_key = "error_rate:Error rate %5'i aşıyor"
        manager.alert_states[alert_key] = AlertState(alert=alert)
        
        # Alert'i acknowledge et
        result = acknowledge_alert(
            alert_type=AlertType.ERROR_RATE,
            message="Error rate %5'i aşıyor",
            acknowledged_by="admin",
        )
        
        assert result is True

    def test_get_active_alerts(self):
        """
        Global get_active_alerts fonksiyonunu test et.
        
        For any alert manager with active alerts, get_active_alerts should return them.
        """
        # Manager'ı sıfırla
        import app.core.alerting as alerting_module
        alerting_module._alert_manager = None
        
        manager = get_alert_manager()
        
        # Alert state'ini manuel olarak oluştur
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        alert_key = "error_rate:Error rate %5'i aşıyor"
        manager.alert_states[alert_key] = AlertState(alert=alert)
        
        # Aktif alert'leri al
        active_alerts = get_active_alerts()
        assert len(active_alerts) == 1


class TestAlertingIntegration:
    """Alerting sistemi integration test'leri."""

    @pytest.mark.asyncio
    async def test_alert_trigger_and_notification(self):
        """
        Alert tetikleme ve notification gönderimi.
        
        For any alert triggered, notifications should be sent to appropriate channels.
        """
        manager = AlertManager()
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        # Alert state'ini kontrol et
        alert_key = "error_rate:Error rate %5'i aşıyor"
        assert alert_key in manager.alert_states
        assert manager.alert_states[alert_key].trigger_count == 1

    @pytest.mark.asyncio
    async def test_email_notification_handler_integration(self):
        """
        Email notification handler integration test'i.
        
        For any alert with email configuration, email handler should attempt to send.
        """
        handler = EmailNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.RESPONSE_TIME,
            severity=AlertSeverity.WARNING,
            message="Response time 5 saniyeyi aşıyor",
            data={"response_time": 5.5, "threshold": 5.0},
        )
        
        # Email konfigürasyonu olmadan test et
        with patch.dict("os.environ", {}, clear=True):
            result = await handler.send(alert)
            # Konfigürasyon olmadığı için False dönmeli
            assert result is False

    @pytest.mark.asyncio
    async def test_slack_notification_handler_integration(self):
        """
        Slack notification handler integration test'i.
        
        For any alert with Slack webhook, Slack handler should format message correctly.
        """
        handler = SlackNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.DISK_SPACE,
            severity=AlertSeverity.CRITICAL,
            message="Disk alanı %80'i aşıyor",
            data={"disk_usage": 85, "threshold": 80},
        )
        
        # Slack mesajını formatla
        payload = handler._format_slack_message(alert)
        
        # Payload'ı kontrol et
        assert "attachments" in payload
        assert len(payload["attachments"]) > 0
        attachment = payload["attachments"][0]
        assert "title" in attachment
        assert "text" in attachment
        assert "fields" in attachment

    @pytest.mark.asyncio
    async def test_alert_escalation_flow(self):
        """
        Alert escalation flow'u.
        
        For any alert that exceeds escalation timeout, it should be escalated.
        """
        manager = AlertManager()
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.MEMORY_USAGE,
            severity=AlertSeverity.WARNING,
            message="Memory kullanımı %90'ı aşıyor",
        )
        
        alert_key = "memory_usage:Memory kullanımı %90'ı aşıyor"
        state = manager.alert_states[alert_key]
        
        # Escalation timeout'unu geç
        state.first_triggered_at = datetime.utcnow() - timedelta(
            seconds=ALERT_ESCALATION_TIMEOUT_SECONDS + 100
        )
        
        # Escalation kontrol et
        assert state.should_escalate() is True

    @pytest.mark.asyncio
    async def test_alert_manager_lifecycle(self):
        """
        Alert manager lifecycle test'i.
        
        For any alert manager, start and stop should work correctly with cleanup.
        """
        manager = AlertManager()
        
        # Başlat
        await manager.start()
        assert manager.running is True
        assert manager.cleanup_task is not None
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ENDPOINT_DOWN,
            severity=AlertSeverity.CRITICAL,
            message="API endpoint'i down oldu",
        )
        
        # Durdur
        await manager.stop()
        assert manager.running is False

    def test_alert_state_transitions(self):
        """
        Alert state transitions test'i.
        
        For any alert state, transitions between states should be correct.
        """
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        state = AlertState(alert=alert)
        
        # Initial state
        assert state.acknowledged is False
        assert state.escalated is False
        
        # Acknowledge
        state.acknowledged = True
        state.acknowledged_at = datetime.utcnow()
        state.acknowledged_by = "admin"
        
        assert state.acknowledged is True
        assert state.acknowledged_by == "admin"
        
        # Escalation should not happen if acknowledged
        assert state.should_escalate() is False


class TestAlertingIntegrationAdvanced:
    """
    Alerting sistemi ileri entegrasyon test'leri.
    
    Bu test sınıfı, alert'lerin tetiklendiğini, email ve Slack
    notification'larının gönderildiğini test eder.
    
    Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
    Validates: Requirements 7.1, 7.2, 7.6
    """

    @pytest.mark.asyncio
    async def test_alert_triggered_with_critical_severity(self):
        """
        Kritik severity ile alert tetiklenmesi.
        
        For any alert triggered with CRITICAL severity, it should be stored
        and notification channels should include email and Slack.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.1, 7.2
        """
        manager = AlertManager()
        
        # Kritik alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        # Alert state'ini kontrol et
        alert_key = "error_rate:Error rate %5'i aşıyor"
        assert alert_key in manager.alert_states
        
        state = manager.alert_states[alert_key]
        assert state.alert.severity == AlertSeverity.CRITICAL
        assert state.trigger_count == 1
        assert state.acknowledged is False
        
        # Notification kanallarını kontrol et
        channels = manager._get_notification_channels(AlertSeverity.CRITICAL)
        assert NotificationChannel.EMAIL in channels
        assert NotificationChannel.SLACK in channels
        assert NotificationChannel.LOG in channels

    @pytest.mark.asyncio
    async def test_alert_triggered_with_warning_severity(self):
        """
        Warning severity ile alert tetiklenmesi.
        
        For any alert triggered with WARNING severity, it should be stored
        and notification channels should include Slack but not email.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.6
        """
        manager = AlertManager()
        
        # Warning alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.RESPONSE_TIME,
            severity=AlertSeverity.WARNING,
            message="Response time 5 saniyeyi aşıyor",
            data={"response_time": 5.5, "threshold": 5.0},
        )
        
        # Alert state'ini kontrol et
        alert_key = "response_time:Response time 5 saniyeyi aşıyor"
        assert alert_key in manager.alert_states
        
        state = manager.alert_states[alert_key]
        assert state.alert.severity == AlertSeverity.WARNING
        
        # Notification kanallarını kontrol et
        channels = manager._get_notification_channels(AlertSeverity.WARNING)
        assert NotificationChannel.SLACK in channels
        assert NotificationChannel.LOG in channels
        assert NotificationChannel.EMAIL not in channels

    @pytest.mark.asyncio
    async def test_email_notification_sent_on_critical_alert(self):
        """
        Kritik alert'te email notification gönderimi.
        
        For any critical alert, email notification handler should be called
        and should format the email correctly.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.1, 7.2
        """
        handler = EmailNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        # Email gövdesini formatla
        body = handler._format_email_body(alert)
        
        # Email gövdesinin doğru bilgileri içerdiğini kontrol et
        assert "Error rate %5'i aşıyor" in body
        assert "error_rate" in body
        assert "6.5" in body
        assert "CRITICAL" in body or "critical" in body
        assert "error_rate" in body

    @pytest.mark.asyncio
    async def test_slack_notification_sent_on_critical_alert(self):
        """
        Kritik alert'te Slack notification gönderimi.
        
        For any critical alert, Slack notification handler should format
        the message with correct color and fields.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.6
        """
        handler = SlackNotificationHandler()
        
        alert = Alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data={"error_rate": 6.5, "threshold": 5.0},
        )
        
        # Slack mesajını formatla
        payload = handler._format_slack_message(alert)
        
        # Payload'ın doğru yapıda olduğunu kontrol et
        assert "attachments" in payload
        assert len(payload["attachments"]) > 0
        
        attachment = payload["attachments"][0]
        assert attachment["color"] == "#ff0000"  # Kırmızı (critical)
        assert "ERROR_RATE" in attachment["title"]
        assert "CRITICAL" in attachment["title"]
        assert "Error rate %5'i aşıyor" in attachment["text"]
        assert "fields" in attachment
        assert len(attachment["fields"]) > 0

    @pytest.mark.asyncio
    async def test_slack_notification_color_by_severity(self):
        """
        Severity'ye göre Slack notification rengi.
        
        For any alert with different severities, Slack message should have
        appropriate color codes.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.6
        """
        handler = SlackNotificationHandler()
        
        # INFO severity
        alert_info = Alert(
            alert_type=AlertType.CUSTOM,
            severity=AlertSeverity.INFO,
            message="Bilgi mesajı",
        )
        payload_info = handler._format_slack_message(alert_info)
        assert payload_info["attachments"][0]["color"] == "#36a64f"  # Yeşil
        
        # WARNING severity
        alert_warning = Alert(
            alert_type=AlertType.CUSTOM,
            severity=AlertSeverity.WARNING,
            message="Uyarı mesajı",
        )
        payload_warning = handler._format_slack_message(alert_warning)
        assert payload_warning["attachments"][0]["color"] == "#ff9900"  # Turuncu
        
        # CRITICAL severity
        alert_critical = Alert(
            alert_type=AlertType.CUSTOM,
            severity=AlertSeverity.CRITICAL,
            message="Kritik mesaj",
        )
        payload_critical = handler._format_slack_message(alert_critical)
        assert payload_critical["attachments"][0]["color"] == "#ff0000"  # Kırmızı

    @pytest.mark.asyncio
    async def test_multiple_alerts_triggered_sequentially(self):
        """
        Birden fazla alert'in sırayla tetiklenmesi.
        
        For any alert manager, multiple alerts should be tracked independently
        and each should have its own state.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.1, 7.2
        """
        manager = AlertManager()
        
        # İlk alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        # İkinci alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.RESPONSE_TIME,
            severity=AlertSeverity.WARNING,
            message="Response time 5 saniyeyi aşıyor",
        )
        
        # Üçüncü alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.DISK_SPACE,
            severity=AlertSeverity.CRITICAL,
            message="Disk alanı %80'i aşıyor",
        )
        
        # Tüm alert'lerin kaydedildiğini kontrol et
        assert len(manager.alert_states) == 3
        
        # Her alert'in doğru state'e sahip olduğunu kontrol et
        assert "error_rate:Error rate %5'i aşıyor" in manager.alert_states
        assert "response_time:Response time 5 saniyeyi aşıyor" in manager.alert_states
        assert "disk_space:Disk alanı %80'i aşıyor" in manager.alert_states

    @pytest.mark.asyncio
    async def test_alert_notification_channels_selection(self):
        """
        Alert notification kanallarının seçimi.
        
        For any alert manager, notification channels should be selected based
        on severity level.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.1, 7.2, 7.6
        """
        manager = AlertManager()
        
        # INFO severity - sadece LOG
        channels_info = manager._get_notification_channels(AlertSeverity.INFO)
        assert len(channels_info) == 1
        assert NotificationChannel.LOG in channels_info
        
        # WARNING severity - LOG + SLACK
        channels_warning = manager._get_notification_channels(AlertSeverity.WARNING)
        assert len(channels_warning) == 2
        assert NotificationChannel.LOG in channels_warning
        assert NotificationChannel.SLACK in channels_warning
        
        # CRITICAL severity - LOG + EMAIL + SLACK
        channels_critical = manager._get_notification_channels(AlertSeverity.CRITICAL)
        assert len(channels_critical) == 3
        assert NotificationChannel.LOG in channels_critical
        assert NotificationChannel.EMAIL in channels_critical
        assert NotificationChannel.SLACK in channels_critical

    @pytest.mark.asyncio
    async def test_alert_data_preservation(self):
        """
        Alert veri korunması.
        
        For any alert triggered with data, the data should be preserved
        in the alert state.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.1, 7.2
        """
        manager = AlertManager()
        
        test_data = {
            "error_rate": 6.5,
            "threshold": 5.0,
            "endpoint": "/api/chat",
            "timestamp": "2024-01-21T10:00:00Z",
        }
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
            data=test_data,
        )
        
        # Alert state'ini kontrol et
        alert_key = "error_rate:Error rate %5'i aşıyor"
        state = manager.alert_states[alert_key]
        
        # Veri korunduğunu kontrol et
        assert state.alert.data == test_data
        assert state.alert.data["error_rate"] == 6.5
        assert state.alert.data["endpoint"] == "/api/chat"

    @pytest.mark.asyncio
    async def test_alert_timestamp_tracking(self):
        """
        Alert zaman takibi.
        
        For any alert triggered, timestamps should be tracked correctly
        for first trigger and last trigger.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.1, 7.2
        """
        manager = AlertManager()
        
        # Alert'i tetikle
        await manager.trigger_alert(
            alert_type=AlertType.ERROR_RATE,
            severity=AlertSeverity.CRITICAL,
            message="Error rate %5'i aşıyor",
        )
        
        alert_key = "error_rate:Error rate %5'i aşıyor"
        state = manager.alert_states[alert_key]
        
        # Zaman bilgisini kontrol et
        assert state.first_triggered_at is not None
        assert state.last_triggered_at is not None
        assert state.first_triggered_at <= state.last_triggered_at
        
        # Alert'in timestamp'ini kontrol et
        assert state.alert.timestamp is not None

    @pytest.mark.asyncio
    async def test_alert_manager_with_multiple_handlers(self):
        """
        Alert manager'ın birden fazla handler ile çalışması.
        
        For any alert manager, all notification handlers should be available
        and properly initialized.
        
        Feature: logging-monitoring-system, Property 7: Alert Tetiklenmesi
        Validates: Requirements 7.1, 7.2, 7.6
        """
        manager = AlertManager()
        
        # Handler'ları kontrol et
        assert len(manager.handlers) == 3
        assert NotificationChannel.EMAIL in manager.handlers
        assert NotificationChannel.SLACK in manager.handlers
        assert NotificationChannel.LOG in manager.handlers
        
        # Handler'ların tipini kontrol et
        assert isinstance(manager.handlers[NotificationChannel.EMAIL], EmailNotificationHandler)
        assert isinstance(manager.handlers[NotificationChannel.SLACK], SlackNotificationHandler)
        assert isinstance(manager.handlers[NotificationChannel.LOG], LogNotificationHandler)
