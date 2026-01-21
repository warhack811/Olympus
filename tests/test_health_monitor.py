"""
Health Monitor ve API Monitoring Test'leri

Bu test dosyası, app/core/health_monitor.py modülünün health monitoring
ve alerting sistemini test eder.

Test Kapsamı:
    - Endpoint metriklerinin kaydedilip kaydedilmediği
    - Health check loop'unun çalışıp çalışmadığı
    - Threshold'ların kontrol edilip edilmediği
    - Alert'lerin tetiklenip tetiklenmediği
    - Health check sonuçlarının log'a yazılıp yazılmadığı
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.core.health_monitor import (
    HealthMonitor,
    EndpointMetric,
    EndpointStats,
    AlertEvent,
    get_health_monitor,
    record_endpoint_metric,
    get_endpoint_stats,
    get_all_endpoint_stats,
    RESPONSE_TIME_THRESHOLD,
    ERROR_RATE_THRESHOLD,
)


class TestEndpointMetric:
    """EndpointMetric veri yapısı test'leri."""

    def test_endpoint_metric_creation(self):
        """
        EndpointMetric'i oluştur ve alanlarını kontrol et.
        
        For any endpoint metric created, all fields should be properly set.
        """
        metric = EndpointMetric(
            endpoint="/api/chat",
            method="POST",
            status_code=200,
            duration_seconds=0.045,
            error=None,
        )
        
        assert metric.endpoint == "/api/chat"
        assert metric.method == "POST"
        assert metric.status_code == 200
        assert metric.duration_seconds == 0.045
        assert metric.error is None
        assert isinstance(metric.timestamp, datetime)

    def test_endpoint_metric_with_error(self):
        """
        Hata ile EndpointMetric'i oluştur.
        
        For any endpoint metric with an error, the error field should be set.
        """
        metric = EndpointMetric(
            endpoint="/api/users",
            method="GET",
            status_code=500,
            duration_seconds=0.123,
            error="Internal Server Error",
        )
        
        assert metric.error == "Internal Server Error"
        assert metric.status_code == 500


class TestEndpointStats:
    """EndpointStats veri yapısı test'leri."""

    def test_endpoint_stats_initialization(self):
        """
        EndpointStats'ı başlat ve başlangıç değerlerini kontrol et.
        
        For any endpoint stats created, initial values should be correct.
        """
        stats = EndpointStats(endpoint="/api/chat", method="POST")
        
        assert stats.endpoint == "/api/chat"
        assert stats.method == "POST"
        assert stats.total_requests == 0
        assert stats.total_errors == 0
        assert stats.avg_duration_seconds == 0.0
        assert stats.error_rate_percent == 0.0

    def test_endpoint_stats_update_single_metric(self):
        """
        EndpointStats'ı tek bir metrik ile güncelle.
        
        For any endpoint stats updated with a single metric, the values should be correct.
        """
        stats = EndpointStats(endpoint="/api/chat", method="POST")
        
        metric = EndpointMetric(
            endpoint="/api/chat",
            method="POST",
            status_code=200,
            duration_seconds=0.045,
            error=None,
        )
        
        stats.update(metric)
        
        assert stats.total_requests == 1
        assert stats.total_errors == 0
        assert stats.avg_duration_seconds == 0.045
        assert stats.max_duration_seconds == 0.045
        assert stats.min_duration_seconds == 0.045
        assert stats.error_rate_percent == 0.0

    def test_endpoint_stats_update_multiple_metrics(self):
        """
        EndpointStats'ı birden fazla metrik ile güncelle.
        
        For any endpoint stats updated with multiple metrics, the average,
        max, and min values should be calculated correctly.
        """
        stats = EndpointStats(endpoint="/api/chat", method="POST")
        
        # Metrik 1: 0.045s, başarılı
        metric1 = EndpointMetric(
            endpoint="/api/chat",
            method="POST",
            status_code=200,
            duration_seconds=0.045,
            error=None,
        )
        stats.update(metric1)
        
        # Metrik 2: 0.123s, başarılı
        metric2 = EndpointMetric(
            endpoint="/api/chat",
            method="POST",
            status_code=200,
            duration_seconds=0.123,
            error=None,
        )
        stats.update(metric2)
        
        # Metrik 3: 0.012s, hata
        metric3 = EndpointMetric(
            endpoint="/api/chat",
            method="POST",
            status_code=500,
            duration_seconds=0.012,
            error="Internal Server Error",
        )
        stats.update(metric3)
        
        assert stats.total_requests == 3
        assert stats.total_errors == 1
        assert abs(stats.avg_duration_seconds - 0.06) < 0.001  # (0.045 + 0.123 + 0.012) / 3
        assert stats.max_duration_seconds == 0.123
        assert stats.min_duration_seconds == 0.012
        assert abs(stats.error_rate_percent - 33.33) < 0.1  # 1/3 * 100


class TestHealthMonitor:
    """HealthMonitor test'leri."""

    @pytest.mark.asyncio
    async def test_health_monitor_start_stop(self):
        """
        Health monitor'ı başlat ve durdur.
        
        For any health monitor, start and stop should work correctly.
        """
        monitor = HealthMonitor()
        
        # Başlat
        await monitor.start()
        assert monitor.running is True
        assert monitor.monitor_task is not None
        
        # Durdur
        await monitor.stop()
        assert monitor.running is False

    def test_health_monitor_record_metric(self):
        """
        Health monitor'a metrik kaydet.
        
        For any metric recorded, it should be stored in the metrics dictionary.
        """
        monitor = HealthMonitor()
        
        monitor.record_metric(
            endpoint="/api/chat",
            method="POST",
            status_code=200,
            duration_seconds=0.045,
            error=None,
        )
        
        assert "/api/chat" in monitor.metrics
        assert len(monitor.metrics["/api/chat"]) == 1
        
        metric = monitor.metrics["/api/chat"][0]
        assert metric.endpoint == "/api/chat"
        assert metric.method == "POST"
        assert metric.status_code == 200
        assert metric.duration_seconds == 0.045

    def test_health_monitor_get_endpoint_stats(self):
        """
        Health monitor'dan endpoint istatistiklerini al.
        
        For any endpoint with recorded metrics, get_endpoint_stats should
        return the correct statistics.
        """
        monitor = HealthMonitor()
        
        # Metrik kaydet
        monitor.record_metric(
            endpoint="/api/users",
            method="GET",
            status_code=200,
            duration_seconds=0.050,
            error=None,
        )
        
        # İstatistikleri güncelle
        monitor._cleanup_old_metrics()
        monitor._update_endpoint_stats()
        
        # İstatistikleri al
        stats = monitor.get_endpoint_stats("/api/users")
        
        assert stats is not None
        assert stats.endpoint == "/api/users"
        assert stats.method == "GET"
        assert stats.total_requests == 1
        assert stats.total_errors == 0

    def test_health_monitor_check_response_time_threshold(self):
        """
        Response time threshold'unu kontrol et.
        
        For any endpoint with average response time exceeding the threshold,
        an alert should be triggered.
        """
        monitor = HealthMonitor()
        
        # Yavaş metrik kaydet (5 saniyeden fazla)
        for i in range(3):
            monitor.record_metric(
                endpoint="/api/slow",
                method="GET",
                status_code=200,
                duration_seconds=6.0,  # 5 saniye threshold'unu aşıyor
                error=None,
            )
        
        # İstatistikleri güncelle
        monitor._cleanup_old_metrics()
        monitor._update_endpoint_stats()
        
        # Threshold'ları kontrol et
        alerts = monitor._check_thresholds()
        
        # Response time alert'i tetiklenmiş olmalı
        response_time_alerts = [a for a in alerts if a.alert_type == "response_time"]
        assert len(response_time_alerts) > 0
        assert response_time_alerts[0].endpoint == "/api/slow"

    def test_health_monitor_check_error_rate_threshold(self):
        """
        Error rate threshold'unu kontrol et.
        
        For any endpoint with error rate exceeding the threshold,
        an alert should be triggered.
        """
        monitor = HealthMonitor()
        
        # Başarılı metrik'ler kaydet
        for i in range(10):
            monitor.record_metric(
                endpoint="/api/unstable",
                method="POST",
                status_code=200,
                duration_seconds=0.050,
                error=None,
            )
        
        # Hata metrik'leri kaydet (%10 error rate)
        for i in range(1):
            monitor.record_metric(
                endpoint="/api/unstable",
                method="POST",
                status_code=500,
                duration_seconds=0.100,
                error="Internal Server Error",
            )
        
        # İstatistikleri güncelle
        monitor._cleanup_old_metrics()
        monitor._update_endpoint_stats()
        
        # Threshold'ları kontrol et
        alerts = monitor._check_thresholds()
        
        # Error rate alert'i tetiklenmiş olmalı (%5 threshold'unu aşıyor)
        error_rate_alerts = [a for a in alerts if a.alert_type == "error_rate"]
        assert len(error_rate_alerts) > 0
        assert error_rate_alerts[0].endpoint == "/api/unstable"

    def test_health_monitor_cleanup_old_metrics(self):
        """
        Eski metrikleri temizle.
        
        For any metrics older than the window, they should be removed.
        """
        monitor = HealthMonitor()
        
        # Yeni metrik kaydet
        monitor.record_metric(
            endpoint="/api/new",
            method="GET",
            status_code=200,
            duration_seconds=0.050,
            error=None,
        )
        
        # Eski metrik kaydet (manuel olarak)
        old_metric = EndpointMetric(
            endpoint="/api/old",
            method="GET",
            status_code=200,
            duration_seconds=0.050,
            error=None,
            timestamp=datetime.utcnow() - timedelta(seconds=400),  # 5 dakikadan eski
        )
        monitor.metrics["/api/old"].append(old_metric)
        
        # Temizle
        monitor._cleanup_old_metrics()
        
        # Yeni metrik hala var olmalı
        assert "/api/new" in monitor.metrics
        # Eski metrik silinmiş olmalı
        assert "/api/old" not in monitor.metrics


class TestGlobalHealthMonitor:
    """Global health monitor fonksiyonları test'leri."""

    def test_get_health_monitor_singleton(self):
        """
        Global health monitor singleton'ını al.
        
        For any call to get_health_monitor, the same instance should be returned.
        """
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        
        assert monitor1 is monitor2

    def test_record_endpoint_metric_global(self):
        """
        Global record_endpoint_metric fonksiyonunu test et.
        
        For any metric recorded via the global function, it should be stored
        in the global health monitor.
        """
        # Önceki metrikleri temizle
        monitor = get_health_monitor()
        monitor.metrics.clear()
        
        # Metrik kaydet
        record_endpoint_metric(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            duration_seconds=0.050,
            error=None,
        )
        
        # Metrik kaydedilmiş olmalı
        assert "/api/test" in monitor.metrics
        assert len(monitor.metrics["/api/test"]) > 0

    def test_get_endpoint_stats_global(self):
        """
        Global get_endpoint_stats fonksiyonunu test et.
        
        For any endpoint with recorded metrics, get_endpoint_stats should
        return the correct statistics.
        """
        # Önceki metrikleri temizle
        monitor = get_health_monitor()
        monitor.metrics.clear()
        monitor.stats.clear()
        
        # Metrik kaydet
        record_endpoint_metric(
            endpoint="/api/global",
            method="POST",
            status_code=200,
            duration_seconds=0.075,
            error=None,
        )
        
        # İstatistikleri güncelle
        monitor._cleanup_old_metrics()
        monitor._update_endpoint_stats()
        
        # İstatistikleri al
        stats = get_endpoint_stats("/api/global")
        
        assert stats is not None
        assert stats.endpoint == "/api/global"
        assert stats.total_requests == 1

    def test_get_all_endpoint_stats_global(self):
        """
        Global get_all_endpoint_stats fonksiyonunu test et.
        
        For any endpoints with recorded metrics, get_all_endpoint_stats should
        return all statistics.
        """
        # Önceki metrikleri temizle
        monitor = get_health_monitor()
        monitor.metrics.clear()
        monitor.stats.clear()
        
        # Birden fazla endpoint için metrik kaydet
        for endpoint in ["/api/users", "/api/chat", "/api/images"]:
            record_endpoint_metric(
                endpoint=endpoint,
                method="GET",
                status_code=200,
                duration_seconds=0.050,
                error=None,
            )
        
        # İstatistikleri güncelle
        monitor._cleanup_old_metrics()
        monitor._update_endpoint_stats()
        
        # Tüm istatistikleri al
        all_stats = get_all_endpoint_stats()
        
        assert len(all_stats) >= 3
        assert "/api/users" in all_stats
        assert "/api/chat" in all_stats
        assert "/api/images" in all_stats


class TestAlertEvent:
    """AlertEvent veri yapısı test'leri."""

    def test_alert_event_creation(self):
        """
        AlertEvent'i oluştur ve alanlarını kontrol et.
        
        For any alert event created, all fields should be properly set.
        """
        alert = AlertEvent(
            alert_type="response_time",
            endpoint="/api/slow",
            method="GET",
            severity="warning",
            message="Response time threshold aşıldı",
            value=6.5,
            threshold=5.0,
        )
        
        assert alert.alert_type == "response_time"
        assert alert.endpoint == "/api/slow"
        assert alert.method == "GET"
        assert alert.severity == "warning"
        assert alert.message == "Response time threshold aşıldı"
        assert alert.value == 6.5
        assert alert.threshold == 5.0
        assert isinstance(alert.timestamp, datetime)


class TestHealthCheckDependencies:
    """Health check'in bağımlılıkları kontrol ettiğini test eden test'ler."""

    @pytest.mark.asyncio
    async def test_health_check_database_connectivity(self):
        """
        Health check'in database bağlantısını kontrol ettiğini test et.
        
        For any health check, it should verify database connectivity
        and return appropriate status.
        """
        from app.core.health import health_checker, HealthStatus
        
        # Database health check'i çalıştır
        result = await health_checker.check_database()
        
        # Sonuç kontrol et
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
        assert result.message is not None
        assert result.timestamp is not None
        
        # Eğer healthy ise response time olmalı
        if result.status == HealthStatus.HEALTHY:
            assert result.response_time_ms is not None
            assert result.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_health_check_redis_connectivity(self):
        """
        Health check'in Redis (cache) bağlantısını kontrol ettiğini test et.
        
        For any health check, it should verify Redis connectivity
        and return appropriate status.
        """
        from app.core.health import health_checker, HealthStatus
        
        # Redis health check'i çalıştır
        result = await health_checker.check_redis()
        
        # Sonuç kontrol et
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.message is not None
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_health_check_chromadb_connectivity(self):
        """
        Health check'in ChromaDB (external service) bağlantısını kontrol ettiğini test et.
        
        For any health check, it should verify ChromaDB connectivity
        and return appropriate status.
        """
        from app.core.health import health_checker, HealthStatus
        
        # ChromaDB health check'i çalıştır
        result = await health_checker.check_chromadb()
        
        # Sonuç kontrol et
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.message is not None
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_health_check_all_dependencies(self):
        """
        Health check'in tüm bağımlılıkları kontrol ettiğini test et.
        
        For any health check, it should check all dependencies
        and return results for each.
        """
        from app.core.health import health_checker
        
        # Tüm health check'leri çalıştır
        results = await health_checker.check_all()
        
        # Sonuçlar kontrol et
        assert "database" in results
        assert "redis" in results
        assert "chromadb" in results
        
        # Her sonuç geçerli olmalı
        for name, result in results.items():
            assert result.status is not None
            assert result.message is not None
            assert result.timestamp is not None


class TestHealthCheckIdempotence:
    """
    Health Check Idempotence Property Test'leri
    
    Property 7: Health Check Idempotence
    For any health check run multiple times on the same system state,
    the results should be consistent (same status, same dependencies checked).
    
    Validates: Requirements 4.6
    """

    @pytest.mark.asyncio
    async def test_health_check_idempotence_database(self):
        """
        Health check'in database kontrol'ünün idempotent olduğunu test et.
        
        For any database health check run multiple times without state changes,
        the results should be identical.
        """
        from app.core.health import health_checker
        
        # Health check'i 3 kez çalıştır
        result1 = await health_checker.check_database()
        result2 = await health_checker.check_database()
        result3 = await health_checker.check_database()
        
        # Tüm sonuçlar aynı status'a sahip olmalı
        assert result1.status == result2.status
        assert result2.status == result3.status
        
        # Tüm sonuçlar aynı mesaja sahip olmalı
        assert result1.message == result2.message
        assert result2.message == result3.message

    @pytest.mark.asyncio
    async def test_health_check_idempotence_redis(self):
        """
        Health check'in Redis kontrol'ünün idempotent olduğunu test et.
        
        For any Redis health check run multiple times without state changes,
        the results should be identical.
        """
        from app.core.health import health_checker
        
        # Health check'i 3 kez çalıştır
        result1 = await health_checker.check_redis()
        result2 = await health_checker.check_redis()
        result3 = await health_checker.check_redis()
        
        # Tüm sonuçlar aynı status'a sahip olmalı
        assert result1.status == result2.status
        assert result2.status == result3.status

    @pytest.mark.asyncio
    async def test_health_check_idempotence_chromadb(self):
        """
        Health check'in ChromaDB kontrol'ünün idempotent olduğunu test et.
        
        For any ChromaDB health check run multiple times without state changes,
        the results should be identical.
        """
        from app.core.health import health_checker
        
        # Health check'i 3 kez çalıştır
        result1 = await health_checker.check_chromadb()
        result2 = await health_checker.check_chromadb()
        result3 = await health_checker.check_chromadb()
        
        # Tüm sonuçlar aynı status'a sahip olmalı
        assert result1.status == result2.status
        assert result2.status == result3.status

    @pytest.mark.asyncio
    async def test_health_check_idempotence_all(self):
        """
        Health check'in tüm bağımlılıkları kontrol'ünün idempotent olduğunu test et.
        
        For any complete health check run multiple times without state changes,
        the results should be identical (same dependencies checked, same statuses).
        """
        from app.core.health import health_checker
        
        # Health check'i 3 kez çalıştır
        results1 = await health_checker.check_all()
        results2 = await health_checker.check_all()
        results3 = await health_checker.check_all()
        
        # Tüm sonuçlar aynı bağımlılıkları kontrol etmeli
        assert set(results1.keys()) == set(results2.keys())
        assert set(results2.keys()) == set(results3.keys())
        
        # Tüm sonuçlar aynı status'a sahip olmalı
        for key in results1.keys():
            assert results1[key].status == results2[key].status
            assert results2[key].status == results3[key].status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

