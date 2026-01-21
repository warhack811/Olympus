"""
Mami AI - Health Check System
==============================

Health check endpoint'leri ve dependency health check'leri.

Best Practices:
- Separate liveness and readiness checks
- Dependency health checks
- Response time tracking
- Graceful degradation

Kullanım:
    GET /health - Basic health check
    GET /health/detailed - Detailed health check with dependencies
    GET /health/ready - Readiness check (can serve traffic?)
    GET /health/live - Liveness check (is process alive?)
"""

import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.feature_flags import feature_enabled

router = APIRouter()


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Health check result."""
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time_ms: float | None = None


class HealthChecker:
    """
    Health check system.
    
    Best Practices:
    - Separate liveness and readiness checks
    - Dependency health checks
    - Response time tracking
    """
    
    async def check_database(self) -> HealthCheckResult:
        """Check database connectivity."""
        start = datetime.utcnow()
        try:
            from app.core.database import get_session
            from sqlalchemy import text
            
            with get_session() as session:
                # Simple query to check connectivity
                session.execute(text("SELECT 1"))
            
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Database connection OK",
                details={"response_time_ms": response_time},
                timestamp=datetime.utcnow(),
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity."""
        start = datetime.utcnow()
        try:
            from app.core.redis_client import get_redis
            
            client = await get_redis()
            if client is None:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Redis not configured",
                    details={},
                    timestamp=datetime.utcnow()
                )
            
            await client.ping()
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Redis connection OK",
                details={"response_time_ms": response_time},
                timestamp=datetime.utcnow(),
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def check_chromadb(self) -> HealthCheckResult:
        """Check ChromaDB connectivity."""
        start = datetime.utcnow()
        try:
            from app.core.database import get_chroma_client, CHROMADB_AVAILABLE
            
            if not CHROMADB_AVAILABLE:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="ChromaDB not available (library not installed)",
                    details={},
                    timestamp=datetime.utcnow()
                )
            
            client = get_chroma_client()
            if client is None:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="ChromaDB not configured",
                    details={},
                    timestamp=datetime.utcnow()
                )
            
            # Simple ping - list collections
            client.list_collections()
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="ChromaDB connection OK",
                details={"response_time_ms": response_time},
                timestamp=datetime.utcnow(),
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"ChromaDB connection failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Check all dependencies."""
        return {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "chromadb": await self.check_chromadb(),
        }


# Global health checker instance
health_checker = HealthChecker()


@router.get("/health")
async def health():
    """
    Basit sağlık endpoint'i.
    
    Mevcut endpoint korunur (backward compatible).
    """
    settings = get_settings()
    now = time.time()

    return {
        "ok": True,
        "app": settings.APP_NAME,
        "env": "dev" if settings.DEBUG else "prod",
        "timestamp": now,
        "features": {
            "chat": feature_enabled("chat", True),
            "image_generation": feature_enabled("image_generation", True),
            "file_upload": feature_enabled("file_upload", True),
            "internet": feature_enabled("internet", True),
            "bela_mode": feature_enabled("bela_mode", True),
            "groq_enabled": feature_enabled("groq_enabled", True),
        },
    }


@router.get("/health/detailed")
async def health_check_detailed():
    """
    Detailed health check with all dependencies.
    
    Returns:
        JSONResponse with status code:
        - 200: All dependencies healthy or degraded
        - 503: At least one dependency unhealthy
    """
    checks = await health_checker.check_all()
    
    # Determine overall status
    statuses = [check.status for check in checks.values()]
    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
        status_code = 503
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
        status_code = 200
    else:
        overall_status = HealthStatus.HEALTHY
        status_code = 200
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "details": check.details
                }
                for name, check in checks.items()
            }
        }
    )


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - can serve traffic?
    
    Critical dependencies must be healthy for the service to be ready.
    
    Returns:
        JSONResponse with status code:
        - 200: Service is ready (critical dependencies healthy)
        - 503: Service is not ready (critical dependencies unhealthy)
    """
    checks = await health_checker.check_all()
    
    # Critical dependencies must be healthy
    critical = ["database"]
    critical_healthy = all(
        checks[name].status == HealthStatus.HEALTHY
        for name in critical
        if name in checks
    )
    
    if not critical_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": "Critical dependencies unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    name: {
                        "status": check.status.value,
                        "message": check.message
                    }
                    for name, check in checks.items()
                    if name in critical
                }
            }
        )
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - is process alive?
    
    Simple check to verify the process is running.
    Used by Kubernetes, Docker, etc. for health probes.
    
    Returns:
        JSONResponse with status code 200 (always, if process is alive)
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
