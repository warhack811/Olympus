"""
Prometheus Metrikleri Collector Test'leri

Bu test dosyası, app/core/metrics.py modülünün Prometheus metrikleri
topladığını ve doğru formatında sunduğunu test eder.

Test Kapsamı:
    - Histogram'ın doğru çalışıp çalışmadığı
    - Counter'ın doğru çalışıp çalışmadığı
    - System metrics'in doğru toplandığı
    - Metrics output'ının Prometheus formatında olduğu

Property 2: Metric Format
Validates: Requirements 3.6
"""

import pytest
from app.core.metrics import (
    request_duration_histogram,
    request_count_counter,
    error_count_counter,
    db_query_duration_histogram,
    cpu_percent_gauge,
    memory_percent_gauge,
    disk_percent_gauge,
    collect_system_metrics,
    get_metrics_output,
    record_request_metrics,
    record_error_metrics,
    record_db_query_metrics,
)


class TestMetricsHistogram:
    """Histogram metrikleri test'leri."""

    def test_request_duration_histogram_observe(self):
        """
        Request duration histogram'ına değer eklenip eklenmediğini test et.
        
        For any request duration value, the histogram should accept and record it.
        """
        # Histogram'a değer ekle
        request_duration_histogram.labels(
            method="GET",
            endpoint="/api/users",
            status=200,
        ).observe(0.045)
        
        # Histogram'ın metric'ini al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Histogram'ın output'ta olduğunu kontrol et
        assert "mami_request_duration_seconds" in metrics_str
        assert 'method="GET"' in metrics_str
        assert 'endpoint="/api/users"' in metrics_str
        assert 'status="200"' in metrics_str

    def test_db_query_duration_histogram_observe(self):
        """
        Database query duration histogram'ına değer eklenip eklenmediğini test et.
        
        For any database query duration value, the histogram should accept and record it.
        """
        # Histogram'a değer ekle
        db_query_duration_histogram.labels(
            query_type="SELECT",
            table="users",
        ).observe(0.012)
        
        # Histogram'ın metric'ini al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Histogram'ın output'ta olduğunu kontrol et
        assert "mami_db_query_duration_seconds" in metrics_str
        assert 'query_type="SELECT"' in metrics_str
        assert 'table="users"' in metrics_str


class TestMetricsCounter:
    """Counter metrikleri test'leri."""

    def test_request_count_counter_increment(self):
        """
        Request count counter'ı artırılıp artırılmadığını test et.
        
        For any request, the counter should increment by 1.
        """
        # Counter'ı artır
        request_count_counter.labels(
            method="POST",
            endpoint="/api/chat",
            status=201,
        ).inc()
        
        # Counter'ın metric'ini al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Counter'ın output'ta olduğunu kontrol et
        assert "mami_request_total" in metrics_str
        assert 'method="POST"' in metrics_str
        assert 'endpoint="/api/chat"' in metrics_str
        assert 'status="201"' in metrics_str

    def test_error_count_counter_increment(self):
        """
        Error count counter'ı artırılıp artırılmadığını test et.
        
        For any error, the counter should increment by 1.
        """
        # Counter'ı artır
        error_count_counter.labels(
            method="GET",
            endpoint="/api/users",
            error_type="ValueError",
        ).inc()
        
        # Counter'ın metric'ini al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Counter'ın output'ta olduğunu kontrol et
        assert "mami_error_total" in metrics_str
        assert 'method="GET"' in metrics_str
        assert 'endpoint="/api/users"' in metrics_str
        assert 'error_type="ValueError"' in metrics_str


class TestSystemMetrics:
    """Sistem metrikleri test'leri."""

    def test_collect_system_metrics_cpu(self):
        """
        CPU metriklerinin toplandığını test et.
        
        For any system, collect_system_metrics should set CPU gauge to a valid value.
        """
        # Sistem metriklerini topla
        collect_system_metrics()
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # CPU metriklerinin output'ta olduğunu kontrol et
        assert "mami_cpu_percent" in metrics_str

    def test_collect_system_metrics_memory(self):
        """
        Memory metriklerinin toplandığını test et.
        
        For any system, collect_system_metrics should set memory gauge to a valid value.
        """
        # Sistem metriklerini topla
        collect_system_metrics()
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Memory metriklerinin output'ta olduğunu kontrol et
        assert "mami_memory_percent" in metrics_str

    def test_collect_system_metrics_disk(self):
        """
        Disk metriklerinin toplandığını test et.
        
        For any system, collect_system_metrics should set disk gauge to a valid value.
        """
        # Sistem metriklerini topla
        collect_system_metrics()
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Disk metriklerinin output'ta olduğunu kontrol et
        assert "mami_disk_percent" in metrics_str


class TestMetricsOutput:
    """Metrics output test'leri."""

    def test_get_metrics_output_format(self):
        """
        Metrics output'ının Prometheus formatında olduğunu test et.
        
        For any metrics request, the output should be in Prometheus text format.
        """
        # Metrikleri al
        metrics_bytes, content_type = get_metrics_output()
        
        # Content type'ı kontrol et
        assert "text/plain" in content_type
        assert "version=" in content_type
        
        # Bytes'ı string'e dönüştür
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Prometheus formatında olduğunu kontrol et
        assert "# HELP" in metrics_str
        assert "# TYPE" in metrics_str
        assert "mami_" in metrics_str

    def test_get_metrics_output_contains_all_metrics(self):
        """
        Metrics output'ının tüm metrikleri içerdiğini test et.
        
        For any metrics request, the output should contain all defined metrics.
        """
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Tüm metriklerin output'ta olduğunu kontrol et
        assert "mami_request_duration_seconds" in metrics_str
        assert "mami_request_total" in metrics_str
        assert "mami_error_total" in metrics_str
        assert "mami_db_query_duration_seconds" in metrics_str
        assert "mami_cpu_percent" in metrics_str
        assert "mami_memory_percent" in metrics_str
        assert "mami_disk_percent" in metrics_str


class TestRecordMetricsFunctions:
    """Metrics recording helper fonksiyonları test'leri."""

    def test_record_request_metrics(self):
        """
        record_request_metrics fonksiyonunun metrikleri kaydettiğini test et.
        
        For any request metrics recorded, the histogram and counter should be updated.
        """
        # Metrikleri kaydet
        record_request_metrics(
            method="GET",
            endpoint="/api/test",
            status_code=200,
            duration_seconds=0.050,
        )
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Metriklerin output'ta olduğunu kontrol et
        assert "mami_request_duration_seconds" in metrics_str
        assert "mami_request_total" in metrics_str
        assert 'method="GET"' in metrics_str
        assert 'endpoint="/api/test"' in metrics_str
        assert 'status="200"' in metrics_str

    def test_record_error_metrics(self):
        """
        record_error_metrics fonksiyonunun metrikleri kaydettiğini test et.
        
        For any error metrics recorded, the error counter should be updated.
        """
        # Metrikleri kaydet
        record_error_metrics(
            method="POST",
            endpoint="/api/test",
            error_type="ValueError",
        )
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Metriklerin output'ta olduğunu kontrol et
        assert "mami_error_total" in metrics_str
        assert 'method="POST"' in metrics_str
        assert 'endpoint="/api/test"' in metrics_str
        assert 'error_type="ValueError"' in metrics_str

    def test_record_db_query_metrics(self):
        """
        record_db_query_metrics fonksiyonunun metrikleri kaydettiğini test et.
        
        For any database query metrics recorded, the histogram should be updated.
        """
        # Metrikleri kaydet
        record_db_query_metrics(
            query_type="SELECT",
            table="users",
            duration_seconds=0.015,
        )
        
        # Metrikleri al
        metrics_bytes, _ = get_metrics_output()
        metrics_str = metrics_bytes.decode("utf-8")
        
        # Metriklerin output'ta olduğunu kontrol et
        assert "mami_db_query_duration_seconds" in metrics_str
        assert 'query_type="SELECT"' in metrics_str
        assert 'table="users"' in metrics_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
