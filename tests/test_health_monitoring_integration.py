"""
Health Monitoring Integration Test'leri

Bu test dosyası, health monitoring sisteminin API ile entegrasyonunu test eder.

Test Kapsamı:
    - Health check endpoint'lerinin çalışıp çalışmadığı
    - Monitoring endpoint'lerinin doğru veri döndürüp döndürmediği
    - Middleware'in health monitor'a metrik kaydettiğini
    - Background health check task'ının çalışıp çalışmadığı
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.health_monitor import (
    get_health_monitor,
    record_endpoint_metric,
    get_endpoint_stats,
)


@pytest.fixture
def health_monitor():
    """Health monitor instance."""
    monitor = get_health_monitor()
    # Önceki metrikleri temizle
    monitor.metrics.clear()
    monitor.stats.clear()
    monitor.alerts.clear()
    return monitor


class TestHealthMonitorBackgroundTask:
    """Health monitor background task test'leri."""

    @pytest.mark.asyncio
    async def test_health_monitor_background_task_runs(self, health_monitor):
        """
        Health monitor background task'ının çalışıp çalışmadığını test et.
        
        For any health monitor started, the background task should run
        periodically and perform health checks.
        """
        # Metrik kaydet
        record_endpoint_metric(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            duration_seconds=0.050,
            error=None,
        )
        
        # Health monitor'ı başlat
        await health_monitor.start()
        
        try:
            # Background task'ın çalışması için biraz bekle
            await asyncio.sleep(0.5)
            
            # Health monitor hala çalışıyor olmalı
            assert health_monitor.running is True
            assert health_monitor.monitor_task is not None
            assert not health_monitor.monitor_task.done()
        finally:
            # Temizle
            await health_monitor.stop()

    @pytest.mark.asyncio
    async def test_health_monitor_performs_health_check(self, health_monitor):
        """
        Health monitor'ın health check'i çalıştırıp çalıştırmadığını test et.
        
        For any health monitor that performs a health check, the endpoint
        statistics should be updated.
        """
        # Metrik kaydet
        for i in range(5):
            record_endpoint_metric(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                duration_seconds=0.050,
                error=None,
            )
        
        # Health check'i çalıştır
        await health_monitor._perform_health_check()
        
        # İstatistikler güncellenmiş olmalı
        stats = health_monitor.get_endpoint_stats("/api/test")
        assert stats is not None
        assert stats.total_requests == 5


class TestThresholdAlerts:
    """Threshold alert'leri test'leri."""

    @pytest.mark.asyncio
    async def test_response_time_alert_triggered(self, health_monitor):
        """
        Response time threshold alert'inin tetiklenip tetiklenmediğini test et.
        
        For any endpoint with average response time exceeding the threshold,
        an alert should be triggered.
        """
        # Yavaş metrik'ler kaydet
        for i in range(3):
            record_endpoint_metric(
                endpoint="/api/slow",
                method="GET",
                status_code=200,
                duration_seconds=6.0,  # 5 saniye threshold'unu aşıyor
                error=None,
            )
        
        # Health check'i çalıştır
        await health_monitor._perform_health_check()
        
        # Alert'ler tetiklenmiş olmalı
        alerts = health_monitor.get_endpoint_alerts("/api/slow")
        response_time_alerts = [a for a in alerts if a.alert_type == "response_time"]
        assert len(response_time_alerts) > 0

    @pytest.mark.asyncio
    async def test_error_rate_alert_triggered(self, health_monitor):
        """
        Error rate threshold alert'inin tetiklenip tetiklenmediğini test et.
        
        For any endpoint with error rate exceeding the threshold,
        an alert should be triggered.
        """
        # Başarılı metrik'ler kaydet
        for i in range(10):
            record_endpoint_metric(
                endpoint="/api/unstable",
                method="POST",
                status_code=200,
                duration_seconds=0.050,
                error=None,
            )
        
        # Hata metrik'leri kaydet (%10 error rate)
        for i in range(1):
            record_endpoint_metric(
                endpoint="/api/unstable",
                method="POST",
                status_code=500,
                duration_seconds=0.100,
                error="Internal Server Error",
            )
        
        # Health check'i çalıştır
        await health_monitor._perform_health_check()
        
        # Alert'ler tetiklenmiş olmalı
        alerts = health_monitor.get_endpoint_alerts("/api/unstable")
        error_rate_alerts = [a for a in alerts if a.alert_type == "error_rate"]
        assert len(error_rate_alerts) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

