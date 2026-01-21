"""
Mami AI - Prometheus Metrikleri Sistemi
========================================

Bu modül, Prometheus formatında performans metriklerini toplar ve sunar.

Özellikler:
    - API request duration histogram'ı
    - API request count counter'ı
    - API error count counter'ı
    - System metrics (CPU, memory, disk) collector'ı
    - Database query time histogram'ı
    - `/metrics` endpoint'i (Prometheus format)

Kullanım:
    from app.core.metrics import (
        request_duration_histogram,
        request_count_counter,
        error_count_counter,
        db_query_duration_histogram,
        get_metrics_registry
    )

    # Request duration'ı kaydet
    request_duration_histogram.observe(0.045)
    
    # Request count'unu artır
    request_count_counter.inc()
    
    # Error count'unu artır
    error_count_counter.inc()
    
    # Database query duration'ı kaydet
    db_query_duration_histogram.observe(0.012)

Prometheus Metrikleri:
    - mami_request_duration_seconds: API request duration (histogram)
    - mami_request_total: API request count (counter)
    - mami_error_total: API error count (counter)
    - mami_db_query_duration_seconds: Database query duration (histogram)
    - mami_cpu_percent: CPU kullanımı (gauge)
    - mami_memory_percent: Memory kullanımı (gauge)
    - mami_disk_percent: Disk kullanımı (gauge)
"""

import psutil
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Optional

# =============================================================================
# PROMETHEUS REGISTRY
# =============================================================================

# Global registry (varsayılan)
_registry: Optional[CollectorRegistry] = None


def get_metrics_registry() -> CollectorRegistry:
    """
    Prometheus registry'sini al veya oluştur.
    
    Returns:
        CollectorRegistry: Prometheus registry nesnesi
    """
    global _registry
    if _registry is None:
        _registry = CollectorRegistry()
    return _registry


# =============================================================================
# METRIK TANIMALARI
# =============================================================================

# API Request Duration Histogram
# Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0 saniye
request_duration_histogram = Histogram(
    name="mami_request_duration_seconds",
    documentation="API isteğinin süresi (saniye)",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    labelnames=["method", "endpoint", "status"],
    registry=get_metrics_registry(),
)

# API Request Count Counter
request_count_counter = Counter(
    name="mami_request_total",
    documentation="Toplam API isteği sayısı",
    labelnames=["method", "endpoint", "status"],
    registry=get_metrics_registry(),
)

# API Error Count Counter
error_count_counter = Counter(
    name="mami_error_total",
    documentation="Toplam API hata sayısı",
    labelnames=["method", "endpoint", "error_type"],
    registry=get_metrics_registry(),
)

# Database Query Duration Histogram
db_query_duration_histogram = Histogram(
    name="mami_db_query_duration_seconds",
    documentation="Veritabanı sorgusu süresi (saniye)",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    labelnames=["query_type", "table"],
    registry=get_metrics_registry(),
)

# System Metrics Gauges
cpu_percent_gauge = Gauge(
    name="mami_cpu_percent",
    documentation="CPU kullanımı (%)",
    registry=get_metrics_registry(),
)

memory_percent_gauge = Gauge(
    name="mami_memory_percent",
    documentation="Memory kullanımı (%)",
    registry=get_metrics_registry(),
)

disk_percent_gauge = Gauge(
    name="mami_disk_percent",
    documentation="Disk kullanımı (%)",
    registry=get_metrics_registry(),
)

# =============================================================================
# SYSTEM METRICS COLLECTOR
# =============================================================================


def collect_system_metrics() -> None:
    """
    Sistem metriklerini topla ve gauge'leri güncelle.
    
    Topladığı metrikler:
    - CPU kullanımı (%)
    - Memory kullanımı (%)
    - Disk kullanımı (%)
    """
    try:
        # CPU kullanımı
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_percent_gauge.set(cpu_percent)
    except Exception:
        # CPU ölçümü başarısız olursa, 0 olarak ayarla
        cpu_percent_gauge.set(0)

    try:
        # Memory kullanımı
        memory_info = psutil.virtual_memory()
        memory_percent_gauge.set(memory_info.percent)
    except Exception:
        # Memory ölçümü başarısız olursa, 0 olarak ayarla
        memory_percent_gauge.set(0)

    try:
        # Disk kullanımı (root partition)
        disk_info = psutil.disk_usage("/")
        disk_percent_gauge.set(disk_info.percent)
    except Exception:
        # Disk ölçümü başarısız olursa, 0 olarak ayarla
        disk_percent_gauge.set(0)


# =============================================================================
# METRICS ENDPOINT
# =============================================================================


def get_metrics_output() -> tuple[bytes, str]:
    """
    Prometheus formatında metrikleri döndür.
    
    Returns:
        tuple: (metrics_bytes, content_type)
        
    Example:
        >>> metrics_bytes, content_type = get_metrics_output()
        >>> print(content_type)
        'text/plain; version=0.0.4; charset=utf-8'
    """
    # Sistem metriklerini güncelle
    collect_system_metrics()
    
    # Prometheus formatında metrikleri döndür
    metrics_bytes = generate_latest(get_metrics_registry())
    content_type = CONTENT_TYPE_LATEST
    
    return metrics_bytes, content_type


# =============================================================================
# HELPER FONKSIYONLAR
# =============================================================================


def record_request_metrics(
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """
    API isteği metriklerini kaydet.
    
    Args:
        method: HTTP metodu (GET, POST, vb.)
        endpoint: API endpoint'i (örn: /api/users)
        status_code: HTTP durum kodu
        duration_seconds: İstek süresi (saniye)
    """
    # Duration histogram'a ekle
    request_duration_histogram.labels(
        method=method,
        endpoint=endpoint,
        status=status_code,
    ).observe(duration_seconds)
    
    # Request count'unu artır
    request_count_counter.labels(
        method=method,
        endpoint=endpoint,
        status=status_code,
    ).inc()


def record_error_metrics(
    method: str,
    endpoint: str,
    error_type: str,
) -> None:
    """
    API hata metriklerini kaydet.
    
    Args:
        method: HTTP metodu (GET, POST, vb.)
        endpoint: API endpoint'i (örn: /api/users)
        error_type: Hata türü (örn: ValueError, DatabaseError)
    """
    # Error count'unu artır
    error_count_counter.labels(
        method=method,
        endpoint=endpoint,
        error_type=error_type,
    ).inc()


def record_db_query_metrics(
    query_type: str,
    table: str,
    duration_seconds: float,
) -> None:
    """
    Veritabanı sorgusu metriklerini kaydet.
    
    Args:
        query_type: Sorgu türü (SELECT, INSERT, UPDATE, DELETE)
        table: Tablo adı
        duration_seconds: Sorgu süresi (saniye)
    """
    # Duration histogram'a ekle
    db_query_duration_histogram.labels(
        query_type=query_type,
        table=table,
    ).observe(duration_seconds)
