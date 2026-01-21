from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from datetime import datetime

from app.config import get_settings
from app.core.feature_flags import feature_enabled, set_feature_flag
from app.core.health import router as health_router  # Health check endpoint'i
from app.core.metrics import get_metrics_output
from app.core.health_monitor import get_all_endpoint_stats, get_endpoint_stats
from app.image.gpu_state import get_state as get_gpu_state
from app.image.image_manager import get_image_queue_stats

# Admin tarafındaki sistem / proje sağlığı endpoint'leri için router.
router = APIRouter(tags=["system"])

# /health endpoint'ini buraya da bağlıyoruz: /api/system/health
router.include_router(health_router)


class FeatureToggleRequest(BaseModel):
    """Admin panelinden bir özelliği açıp kapatma isteği için şema."""

    key: str
    enabled: bool


@router.get("/features")
async def list_features():
    """Önemli feature flag'lerin mevcut durumunu döner."""
    keys = [
        "chat",
        "image_generation",
        "file_upload",
        "internet",
        "bela_mode",
        "groq_enabled",
    ]
    return {"features": {k: feature_enabled(k, True) for k in keys}}


@router.post("/features/toggle")
async def toggle_feature(body: FeatureToggleRequest):
    """Tek bir feature flag'i açar veya kapatır."""
    set_feature_flag(body.key, body.enabled)
    return {
        "ok": True,
        "key": body.key,
        "enabled": feature_enabled(body.key),
    }


@router.get("/overview")
async def system_overview():
    """Admin proje sağlığı ekranı için genel sistem durumunu döner."""
    settings = get_settings()

    # GPU durumu (Gemma / Flux)
    gpu_state = get_gpu_state()

    # Image kuyruğu istatistikleri
    queue_stats = get_image_queue_stats()

    # Önemli feature'ların durumu
    feature_keys = [
        "chat",
        "image_generation",
        "file_upload",
        "internet",
        "bela_mode",
        "groq_enabled",
    ]
    features = {k: feature_enabled(k, True) for k in feature_keys}

    return {
        "ok": True,
        "app": settings.APP_NAME,
        "env": "dev" if settings.DEBUG else "prod",
        "host": settings.API_HOST,
        "port": settings.API_PORT,
        "gpu_state": str(gpu_state.value) if hasattr(gpu_state, "value") else str(gpu_state),
        "image_queue": queue_stats,
        "features": features,
    }


@router.get("/metrics")
async def metrics():
    """
    Prometheus formatında metrikleri döndür.
    
    Bu endpoint, Prometheus tarafından scrape edilir ve sistem performansı
    metriklerini sağlar:
    - API request duration
    - API request count
    - API error count
    - Database query duration
    - System metrics (CPU, memory, disk)
    
    Returns:
        Response: Prometheus formatında metrikler
    """
    metrics_bytes, content_type = get_metrics_output()
    return Response(content=metrics_bytes, media_type=content_type)


@router.get("/monitoring/endpoints")
async def get_endpoint_monitoring():
    """
    Tüm API endpoint'lerinin monitoring istatistiklerini döndür.
    
    Her endpoint için:
    - Toplam request sayısı
    - Toplam error sayısı
    - Ortalama response time
    - Maksimum response time
    - Minimum response time
    - Error rate (%)
    - Son hata mesajı ve zamanı
    
    Returns:
        Dict: Endpoint istatistikleri
    """
    stats = get_all_endpoint_stats()
    
    return {
        "ok": True,
        "endpoints": {
            endpoint: {
                "method": stat.method,
                "total_requests": stat.total_requests,
                "total_errors": stat.total_errors,
                "avg_duration_seconds": round(stat.avg_duration_seconds, 4),
                "max_duration_seconds": round(stat.max_duration_seconds, 4),
                "min_duration_seconds": round(stat.min_duration_seconds, 4),
                "error_rate_percent": round(stat.error_rate_percent, 2),
                "last_error": stat.last_error,
                "last_error_time": stat.last_error_time.isoformat() if stat.last_error_time else None,
            }
            for endpoint, stat in stats.items()
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/monitoring/endpoints/{endpoint_path:path}")
async def get_endpoint_monitoring_detail(endpoint_path: str):
    """
    Belirli bir endpoint'in monitoring istatistiklerini döndür.
    
    Args:
        endpoint_path: Endpoint yolu (örn: api/chat)
    
    Returns:
        Dict: Endpoint istatistikleri veya 404
    """
    # Endpoint yolunu düzelt
    endpoint = f"/{endpoint_path}"
    
    stat = get_endpoint_stats(endpoint)
    if not stat:
        return {
            "ok": False,
            "error": "Endpoint not found",
            "endpoint": endpoint,
        }
    
    return {
        "ok": True,
        "endpoint": endpoint,
        "method": stat.method,
        "total_requests": stat.total_requests,
        "total_errors": stat.total_errors,
        "avg_duration_seconds": round(stat.avg_duration_seconds, 4),
        "max_duration_seconds": round(stat.max_duration_seconds, 4),
        "min_duration_seconds": round(stat.min_duration_seconds, 4),
        "error_rate_percent": round(stat.error_rate_percent, 2),
        "last_error": stat.last_error,
        "last_error_time": stat.last_error_time.isoformat() if stat.last_error_time else None,
        "timestamp": datetime.utcnow().isoformat(),
    }
