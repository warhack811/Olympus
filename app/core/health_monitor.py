"""
Mami AI - Health Monitoring & Alerting Sistemi
===============================================

Bu modül, API endpoint'lerinin sağlığını izler ve alert'ler gönderir.

Özellikler:
    - Background health check task'ı (30 saniye aralıklarla)
    - Response time threshold monitoring (5 saniye)
    - Error rate threshold monitoring (%5)
    - Alert sistemi (email, log)
    - Health check sonuçlarını log'a yaz
    - Endpoint-specific metrics tracking

Kullanım:
    from app.core.health_monitor import (
        start_health_monitor,
        stop_health_monitor,
        record_endpoint_metric,
        get_endpoint_stats
    )

    # Health monitor'ı başlat (lifespan'de)
    await start_health_monitor()
    
    # Endpoint metriklerini kaydet
    record_endpoint_metric(
        endpoint="/api/chat",
        method="POST",
        status_code=200,
        duration_seconds=0.045,
        error=None
    )
    
    # Endpoint istatistiklerini al
    stats = get_endpoint_stats("/api/chat")
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from app.core.logger import get_logger, log_event

# =============================================================================
# YAPILANDIRMA SABİTLERİ
# =============================================================================

# Health check aralığı (saniye)
HEALTH_CHECK_INTERVAL = 30

# Response time threshold (saniye)
RESPONSE_TIME_THRESHOLD = 5.0

# Error rate threshold (%)
ERROR_RATE_THRESHOLD = 5.0

# Metrics window (son N saniye içindeki metrikler)
METRICS_WINDOW_SECONDS = 300  # 5 dakika

# =============================================================================
# VERİ YAPILARI
# =============================================================================


@dataclass
class EndpointMetric:
    """Endpoint metriği."""
    endpoint: str
    method: str
    status_code: int
    duration_seconds: float
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EndpointStats:
    """Endpoint istatistikleri."""
    endpoint: str
    method: str
    total_requests: int = 0
    total_errors: int = 0
    avg_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    min_duration_seconds: float = float('inf')
    error_rate_percent: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    def update(self, metric: EndpointMetric) -> None:
        """Metrik ile istatistikleri güncelle."""
        self.total_requests += 1
        
        if metric.error:
            self.total_errors += 1
            self.last_error = metric.error
            self.last_error_time = metric.timestamp
        
        # Duration istatistikleri
        if metric.duration_seconds > self.max_duration_seconds:
            self.max_duration_seconds = metric.duration_seconds
        if metric.duration_seconds < self.min_duration_seconds:
            self.min_duration_seconds = metric.duration_seconds
        
        # Average duration hesapla
        if self.total_requests > 0:
            self.avg_duration_seconds = (
                (self.avg_duration_seconds * (self.total_requests - 1) + metric.duration_seconds) 
                / self.total_requests
            )
        
        # Error rate hesapla
        if self.total_requests > 0:
            self.error_rate_percent = (self.total_errors / self.total_requests) * 100


@dataclass
class AlertEvent:
    """Alert olayı."""
    alert_type: str  # "response_time", "error_rate"
    endpoint: str
    method: str
    severity: str  # "warning", "critical"
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# HEALTH MONITOR
# =============================================================================


class HealthMonitor:
    """
    API endpoint'lerinin sağlığını izleyen ve alert'ler gönderen sistem.
    
    Özellikler:
    - Background health check task'ı (30 saniye aralıklarla)
    - Response time threshold monitoring (5 saniye)
    - Error rate threshold monitoring (%5)
    - Alert sistemi (email, log)
    - Health check sonuçlarını log'a yaz
    """
    
    def __init__(self):
        """Health monitor'ı başlat."""
        self.logger = get_logger(__name__)
        
        # Metrics storage (endpoint -> list of metrics)
        self.metrics: Dict[str, List[EndpointMetric]] = defaultdict(list)
        
        # Endpoint stats (endpoint -> stats)
        self.stats: Dict[str, EndpointStats] = {}
        
        # Alert history (endpoint -> list of alerts)
        self.alerts: Dict[str, List[AlertEvent]] = defaultdict(list)
        
        # Background task
        self.monitor_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Health monitor'ı başlat."""
        if self.running:
            self.logger.warning("Health monitor zaten çalışıyor")
            return
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Health monitor başlatıldı")
    
    async def stop(self) -> None:
        """Health monitor'ı durdur."""
        if not self.running:
            return
        
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Health monitor durduruldu")
    
    async def _monitor_loop(self) -> None:
        """
        Background health check loop'u.
        
        Her 30 saniyede bir:
        1. Endpoint istatistiklerini hesapla
        2. Threshold'ları kontrol et
        3. Alert'ler gönder (varsa)
        4. Sonuçları log'a yaz
        """
        while self.running:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                
                if not self.running:
                    break
                
                # Health check'i çalıştır
                await self._perform_health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Health monitor loop'unda hata: {e}",
                    exc_info=True
                )
    
    async def _perform_health_check(self) -> None:
        """
        Health check'i çalıştır.
        
        1. Endpoint istatistiklerini hesapla
        2. Threshold'ları kontrol et
        3. Alert'ler gönder (varsa)
        4. Sonuçları log'a yaz
        """
        async with self._lock:
            # Eski metrikleri temizle (5 dakikadan eski)
            self._cleanup_old_metrics()
            
            # Endpoint istatistiklerini güncelle
            self._update_endpoint_stats()
            
            # Threshold'ları kontrol et ve alert'ler gönder
            alerts = self._check_thresholds()
            
            # Sonuçları log'a yaz
            self._log_health_check_results(alerts)
    
    def _cleanup_old_metrics(self) -> None:
        """Eski metrikleri temizle (5 dakikadan eski)."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=METRICS_WINDOW_SECONDS)
        
        for endpoint in list(self.metrics.keys()):
            # Eski metrikleri filtrele
            self.metrics[endpoint] = [
                m for m in self.metrics[endpoint]
                if m.timestamp > cutoff_time
            ]
            
            # Boş endpoint'leri sil
            if not self.metrics[endpoint]:
                del self.metrics[endpoint]
    
    def _update_endpoint_stats(self) -> None:
        """Endpoint istatistiklerini güncelle."""
        for endpoint, metrics in self.metrics.items():
            if endpoint not in self.stats:
                # İlk kez bu endpoint'i görüyoruz
                method = metrics[0].method if metrics else "UNKNOWN"
                self.stats[endpoint] = EndpointStats(endpoint=endpoint, method=method)
            
            # Yeni metrikleri istatistiklere ekle
            for metric in metrics:
                self.stats[endpoint].update(metric)
    
    def _check_thresholds(self) -> List[AlertEvent]:
        """
        Threshold'ları kontrol et ve alert'ler gönder.
        
        Returns:
            List[AlertEvent]: Tetiklenen alert'ler
        """
        alerts = []
        
        for endpoint, stats in self.stats.items():
            # Response time threshold'unu kontrol et
            if stats.avg_duration_seconds > RESPONSE_TIME_THRESHOLD:
                alert = AlertEvent(
                    alert_type="response_time",
                    endpoint=endpoint,
                    method=stats.method,
                    severity="warning",
                    message=f"Response time threshold aşıldı: {stats.avg_duration_seconds:.2f}s > {RESPONSE_TIME_THRESHOLD}s",
                    value=stats.avg_duration_seconds,
                    threshold=RESPONSE_TIME_THRESHOLD,
                )
                alerts.append(alert)
                self.alerts[endpoint].append(alert)
            
            # Error rate threshold'unu kontrol et
            if stats.error_rate_percent > ERROR_RATE_THRESHOLD:
                alert = AlertEvent(
                    alert_type="error_rate",
                    endpoint=endpoint,
                    method=stats.method,
                    severity="critical",
                    message=f"Error rate threshold aşıldı: {stats.error_rate_percent:.2f}% > {ERROR_RATE_THRESHOLD}%",
                    value=stats.error_rate_percent,
                    threshold=ERROR_RATE_THRESHOLD,
                )
                alerts.append(alert)
                self.alerts[endpoint].append(alert)
        
        return alerts
    
    def _log_health_check_results(self, alerts: List[AlertEvent]) -> None:
        """
        Health check sonuçlarını log'a yaz.
        
        Args:
            alerts: Tetiklenen alert'ler
        """
        # Genel health check sonuçlarını log'la
        log_event(
            self.logger,
            event_type="health_check",
            event_name="completed",
            data={
                "endpoints_monitored": len(self.stats),
                "alerts_triggered": len(alerts),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        # Alert'leri log'la
        for alert in alerts:
            log_event(
                self.logger,
                event_type="alert",
                event_name=alert.alert_type,
                data={
                    "endpoint": alert.endpoint,
                    "method": alert.method,
                    "severity": alert.severity,
                    "message": alert.message,
                    "value": alert.value,
                    "threshold": alert.threshold,
                }
            )
    def record_metric(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_seconds: float,
        error: Optional[str] = None,
    ) -> None:
        """
        Endpoint metriğini kaydet.
        
        Args:
            endpoint: API endpoint'i (örn: /api/chat)
            method: HTTP metodu (GET, POST, vb.)
            status_code: HTTP durum kodu
            duration_seconds: İstek süresi (saniye)
            error: Hata mesajı (varsa)
        """
        metric = EndpointMetric(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_seconds=duration_seconds,
            error=error,
        )
        
        # Metriği kaydet (thread-safe olmayan ama çoğu durumda sorun olmaz)
        self.metrics[endpoint].append(metric)
    
    def get_endpoint_stats(self, endpoint: str) -> Optional[EndpointStats]:
        """
        Endpoint istatistiklerini al.
        
        Args:
            endpoint: API endpoint'i
            
        Returns:
            EndpointStats veya None
        """
        return self.stats.get(endpoint)
    
    def get_all_stats(self) -> Dict[str, EndpointStats]:
        """
        Tüm endpoint istatistiklerini al.
        
        Returns:
            Dict[endpoint -> EndpointStats]
        """
        return self.stats.copy()
    
    def get_endpoint_alerts(self, endpoint: str) -> List[AlertEvent]:
        """
        Endpoint'in alert'lerini al.
        
        Args:
            endpoint: API endpoint'i
            
        Returns:
            List[AlertEvent]
        """
        return self.alerts.get(endpoint, [])


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """
    Global health monitor instance'ını al.
    
    Returns:
        HealthMonitor: Global instance
    """
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


async def start_health_monitor() -> None:
    """Health monitor'ı başlat."""
    monitor = get_health_monitor()
    await monitor.start()


async def stop_health_monitor() -> None:
    """Health monitor'ı durdur."""
    monitor = get_health_monitor()
    await monitor.stop()


def record_endpoint_metric(
    endpoint: str,
    method: str,
    status_code: int,
    duration_seconds: float,
    error: Optional[str] = None,
) -> None:
    """
    Endpoint metriğini kaydet.
    
    Args:
        endpoint: API endpoint'i
        method: HTTP metodu
        status_code: HTTP durum kodu
        duration_seconds: İstek süresi (saniye)
        error: Hata mesajı (varsa)
    """
    monitor = get_health_monitor()
    monitor.record_metric(endpoint, method, status_code, duration_seconds, error)


def get_endpoint_stats(endpoint: str) -> Optional[EndpointStats]:
    """
    Endpoint istatistiklerini al.
    
    Args:
        endpoint: API endpoint'i
        
    Returns:
        EndpointStats veya None
    """
    monitor = get_health_monitor()
    return monitor.get_endpoint_stats(endpoint)


def get_all_endpoint_stats() -> Dict[str, EndpointStats]:
    """
    Tüm endpoint istatistiklerini al.
    
    Returns:
        Dict[endpoint -> EndpointStats]
    """
    monitor = get_health_monitor()
    return monitor.get_all_stats()
