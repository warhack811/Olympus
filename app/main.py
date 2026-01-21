"""
Mami AI - Ana Uygulama Giriş Noktası
====================================

Bu modül, FastAPI uygulamasını başlatır ve yapılandırır.

Başlatma:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

veya eski yol (hala çalışır):
    uvicorn main:app --reload

Özellikler:
    - CORS middleware
    - Session middleware
    - Statik dosya sunumu (UI, images)
    - API route'ları
    - WebSocket desteği
    - Otomatik veritabanı başlatma
"""

import sys
import os
import logging
from pathlib import Path
from time import perf_counter

# Proje kök dizinini Python path'e ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth.invite_manager import ensure_initial_invite
from app.auth.session import get_username_from_request

# Resolvers
# Auth
from app.auth.user_manager import ensure_default_admin, get_user_by_username

# Yapılandırma
from app.config import get_settings
from app.core.database import init_database_with_defaults
from app.core.exceptions import MamiException

# Core modüller
from app.core.logger import get_logger, log_request, log_response, log_error, set_request_id, clear_request_id
from app.core.metrics import record_request_metrics, record_error_metrics
from app.core.health_monitor import start_health_monitor, stop_health_monitor, record_endpoint_metric
from app.memory.conversation import set_user_resolver as set_conv_user_resolver
from app.memory.store import set_user_resolver as set_memory_user_resolver

# =============================================================================
# YAPILANDIRMA
# =============================================================================

settings = get_settings()
from app.core.logger import get_logger, configure_root_logger

# Root logger yapılandırması (Kütüphane logları ve genel çıktı için)
configure_root_logger(logging.INFO)

logger = get_logger(__name__)

# =============================================================================
# USER RESOLVER
# =============================================================================


def _resolve_user_id(username: str):
    """Username -> user_id çözmek için ortak resolver."""
    user = get_user_by_username(username)
    return user.id if user else None


# Resolver'ları ayarla
set_memory_user_resolver(_resolve_user_id)
set_conv_user_resolver(_resolve_user_id)

# =============================================================================
# STARTUP INIT (Module Level - runs once on import)
# =============================================================================

# Database init (sync, runs on module load)
logger.info("Initializing database...")
from app.core.database import init_database_with_defaults
init_database_with_defaults()

# Maintenance Scheduler (sync, daemon thread)
if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
    from app.core.maintenance import start_maintenance_scheduler
    start_maintenance_scheduler()
    logger.info("Maintenance scheduler started")

# =============================================================================
# LIFESPAN CONTEXT (ONLY async tasks)
# =============================================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - ONLY async background tasks"""
    import asyncio
    
    logger.info("Application starting...")
    
    # Health Monitor başlat
    try:
        await start_health_monitor()
        logger.info("Health monitor başlatıldı")
    except Exception as e:
        logger.error(f"Health monitor başlatılamadı: {e}", exc_info=True)
    
    # Alert Manager başlat
    try:
        from app.core.alerting import start_alert_manager
        await start_alert_manager()
        logger.info("Alert manager başlatıldı")
    except Exception as e:
        logger.error(f"Alert manager başlatılamadı: {e}", exc_info=True)
    
    # Redis Bridge for WebSocket image progress
    try:
        from app.core.websockets import start_redis_bridge
        
        bridge_task = asyncio.create_task(start_redis_bridge())
        
        def bridge_error_handler(task):
            try:
                task.result()
            except Exception as e:
                logger.error(f"Redis Bridge error: {e}", exc_info=True)
        
        bridge_task.add_done_callback(bridge_error_handler)
        logger.info("Redis WebSocket bridge started")
        
    except Exception as e:
        logger.error(f"Failed to start Redis bridge: {e}", exc_info=True)

    # RAG FTS initialization
    try:
        from app.services.brain.rag_fts import init_rag_fts
        asyncio.create_task(init_rag_fts())
    except ImportError:
        pass  # RAG FTS optional
    except Exception as e:
        logger.error(f"RAG FTS initialization error: {e}")

    # Startup Checks
    try:
        from app.auth.user_manager import ensure_default_admin
        from app.auth.invite_manager import ensure_initial_invite
        
        await ensure_default_admin()
        await ensure_initial_invite()
        logger.info("Startup checks completed (Admin & Invites)")
    except Exception as e:
        logger.error(f"Startup check failed: {e}")

    logger.info("Application ready")
    
    yield  # App runs
    
    logger.info("Application shutting down...")
    
    # Analytics Tracker'ı kapat (pending event'leri flush et)
    try:
        from app.core.analytics import get_analytics_tracker
        tracker = get_analytics_tracker()
        tracker.shutdown()
        logger.info("Analytics tracker kapatıldı")
    except Exception as e:
        logger.error(f"Analytics tracker kapatılırken hata: {e}", exc_info=True)
    
    # Health Monitor'ı durdur
    try:
        await stop_health_monitor()
        logger.info("Health monitor durduruldu")
    except Exception as e:
        logger.error(f"Health monitor durdurulurken hata: {e}", exc_info=True)
    
    # Alert Manager'ı durdur
    try:
        from app.core.alerting import stop_alert_manager
        await stop_alert_manager()
        logger.info("Alert manager durduruldu")
    except Exception as e:
        logger.error(f"Alert manager durdurulurken hata: {e}", exc_info=True)

# =============================================================================
# FASTAPI UYGULAMASI (with lifespan)
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="Mami AI - Gelişmiş AI Asistan",
    version="4.2.0",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,  # MODERN LIFESPAN
)

# =============================================================================
# MIDDLEWARE
# =============================================================================

# Session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS middleware - X-Conversation-ID header'ını expose et
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://olympus-dyvv.vercel.app",
        "https://mami-ai-core.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-ID"],  # Frontend bu header'ı okuyabilmeli
)


# Request logging middleware - JSON formatında yapılandırılmış logging
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    HTTP isteklerini ve yanıtlarını JSON formatında log'lar ve metrikleri toplar.
    
    Özellikler:
    - Request ID (correlation ID) oluşturur ve tracking'i sağlar
    - Request başlangıcında request bilgilerini log'lar
    - Response tamamlandığında response bilgilerini log'lar
    - Hata durumunda error bilgilerini log'lar
    - Performance timing'i ölçer (request duration)
    - Prometheus metrikleri toplar:
      * Request duration histogram'ına ekle
      * Request count counter'ını artır
      * Error count counter'ını artır (hata durumunda)
    """
    import uuid
    
    start = perf_counter()
    user = None
    request_id = None
    
    try:
        # Request ID oluştur ve ayarla (correlation ID)
        request_id = str(uuid.uuid4())[:8]
        set_request_id(request_id)
        
        # Kullanıcı bilgisini al (varsa)
        try:
            user = get_username_from_request(request)
        except Exception:
            pass

        # Request'i log'la
        log_request(
            logger,
            request.method,
            request.url.path,
            user=user,
            headers={"content-type": request.headers.get("content-type", "")},
            query_params=dict(request.query_params) if request.query_params else None,
            extra={"request_id": request_id}
        )
        
        # Request'i işle
        try:
            response = await call_next(request)
        except Exception as exc:
            # Hata durumunda error logging
            duration_ms = (perf_counter() - start) * 1000
            duration_seconds = duration_ms / 1000
            
            log_error(
                logger,
                f"İstek işlenirken hata oluştu: {str(exc)}",
                error_type=type(exc).__name__,
                user=user,
                path=request.url.path,
                extra={
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                    "method": request.method,
                },
                exc_info=True
            )
            
            # Hata metriklerini kaydet
            record_error_metrics(
                method=request.method,
                endpoint=request.url.path,
                error_type=type(exc).__name__,
            )
            
            # Health monitor'a metrik kaydet (error)
            record_endpoint_metric(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                duration_seconds=duration_seconds,
                error=str(exc),
            )
            
            clear_request_id()
            raise
        
        # Response'u log'la
        duration_ms = (perf_counter() - start) * 1000
        duration_seconds = duration_ms / 1000
        
        log_response(
            logger,
            response.status_code,
            duration_ms,
            user=user,
            path=request.url.path,
            extra={
                "request_id": request_id,
                "method": request.method,
                "content_type": response.headers.get("content-type", ""),
            }
        )
        
        # Metrikleri kaydet (Prometheus)
        # 1. Request duration histogram'ına ekle
        # 2. Request count counter'ını artır
        # 3. Status code'u counter'a ekle
        record_request_metrics(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )
        
        # Health monitor'a metrik kaydet
        record_endpoint_metric(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_seconds=duration_seconds,
            error=None,
        )
        
        return response
        
    finally:
        # Request ID'sini temizle
        clear_request_id()


# =============================================================================
# STATİK DOSYALAR
# =============================================================================

BASE_DIR = project_root
# UI_DIR artık yeni React build çıktısını (dist) gösteriyor
UI_DIR = BASE_DIR / "ui-new" / "dist"
IMAGES_DIR = BASE_DIR / "data" / "images"
UPLOADS_DIR = BASE_DIR / "data" / "uploads"

# Dizinleri oluştur
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
# /assets -> Vite tarafından üretilen JS/CSS dosyaları
if (UI_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(UI_DIR / "assets")), name="assets")

# /images -> Kullanıcı yüklemeleri (CORS Enabled for Cross-Domain Downloads)
class ImageStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

app.mount("/images", ImageStaticFiles(directory=str(IMAGES_DIR)), name="images")
app.mount("/uploads", ImageStaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================


@app.exception_handler(MamiException)
async def mami_exception_handler(request: Request, exc: MamiException):
    """MamiException türündeki hataları yakalar."""
    logger.error(f"[EXCEPTION] {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": True,
            "message": exc.user_message,
            "detail": exc.message if settings.DEBUG else None,
        },
    )


# =============================================================================
# ROUTES (old on_event removed, using lifespan now)
# =============================================================================

from http.cookies import SimpleCookie

from app.auth.dependencies import SESSION_COOKIE_NAME
from app.auth.session import get_user_from_session_token

# WebSocket bağlantıları - websocket_sender.py ile aynı isim olmalı!
from app.core.websockets import connected


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    from app.core.websockets import register_connection, unregister_connection
    await ws.accept()

    user = None
    try:
        # WebSocket'te cookies'e scope üzerinden erişim
        cookies = {}
        for header_name, header_value in ws.scope.get("headers", []):
            if header_name == b"cookie":
                cookie = SimpleCookie()
                cookie.load(header_value.decode("utf-8"))
                for key, morsel in cookie.items():
                    cookies[key] = morsel.value
                break

        token = cookies.get(SESSION_COOKIE_NAME)
        if not token:
            logger.warning("[WEBSOCKET] Attempt without session cookie. Closing.")
            await ws.close(code=1008) # Policy Violation
            return

        user = get_user_from_session_token(token)
        if not user:
            logger.warning(f"[WEBSOCKET] Invalid token: {token[:8]}... Closing.")
            await ws.close(code=1008)
            return
            
        # Success: Register connection
        register_connection(ws, user.id, user.username)
        logger.info(f"[WEBSOCKET] Authenticated user: {user.username}")
            
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")

    username = user.username if user else "anonymous"
    logger.info(f"[WEBSOCKET] Yeni bağlantı: {username}")

    try:
        while True:
            await ws.receive_text()
    except Exception as e:
        logger.debug(f"[WEBSOCKET] Bağlantı kapandı ({username}): {e}")
    finally:
        unregister_connection(ws)
        logger.info(f"[WEBSOCKET] Bağlantı kaldırıldı: {username}")


# =============================================================================
# API ROUTE'LARI
# =============================================================================

from app.api import (
    admin_api_keys,  # Direct module import
    admin_routes,
    auth_routes,
    public_routes,
    system_routes,
)

# from app.api import user_routes  # DEPRECATED - Moved to app/api/routes/*
# New modular routes
from app.api.routes import analytics, chat, documents, images, memories, preferences

# API v1 (Yeni standart yol)
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["v1-auth"])
app.include_router(public_routes.router, prefix="/api/v1/public", tags=["v1-public"])
# app.include_router(user_routes.router, prefix="/api/v1/user", tags=["v1-user"])  # DEPRECATED
app.include_router(chat.router, prefix="/api/v1/user", tags=["v1-chat"])
app.include_router(memories.router, prefix="/api/v1/user", tags=["v1-memories"])
app.include_router(documents.router, prefix="/api/v1/user", tags=["v1-documents"])
app.include_router(images.router, prefix="/api/v1/user", tags=["v1-images"])
app.include_router(preferences.router, prefix="/api/v1/user", tags=["v1-preferences"])
app.include_router(analytics.router, prefix="/api/v1/user", tags=["v1-analytics"])
app.include_router(admin_routes.router, prefix="/api/v1/admin", tags=["v1-admin"])
app.include_router(system_routes.router, prefix="/api/v1/system", tags=["v1-system"])
app.include_router(admin_api_keys.router, prefix="/api/v1/admin", tags=["v1-admin"])  # Route Prefix aynı (admin)
# Reload Trigger 14 (Settings Integrated)

# Backward Compatibility (Eski yollar da çalışır)
app.include_router(public_routes.router, prefix="/api/public", include_in_schema=False)
# app.include_router(user_routes.router, prefix="/api/user", include_in_schema=False) # DEPRECATED
app.include_router(chat.router, prefix="/api/user", include_in_schema=False)
app.include_router(memories.router, prefix="/api/user", include_in_schema=False)
app.include_router(documents.router, prefix="/api/user", include_in_schema=False)
app.include_router(images.router, prefix="/api/user", include_in_schema=False)
app.include_router(preferences.router, prefix="/api/user", include_in_schema=False)
app.include_router(analytics.router, prefix="/api/user", include_in_schema=False)
app.include_router(admin_routes.router, prefix="/api/admin", include_in_schema=False)
app.include_router(system_routes.router, prefix="/api/system", include_in_schema=False)

logger.info("API route'ları yüklendi (v1 + backward compat)")

# =============================================================================
# TEMEL ENDPOINT'LER & SPA HANDLER (EN SONA)
# =============================================================================


@app.get("/health")
async def health_check():
    """Sağlık kontrolü endpoint'i."""
    return {"status": "ok", "app": settings.APP_NAME}


# Dosya uzantısı olan istekleri (resim, manifest vb.) dist klasöründen direkt sunmaya çalış
@app.get("/{path:path}")
async def serve_spa(request: Request, path: str):
    """
    Single Page Application (SPA) Handler.

    Tüm bilinmeyen istekleri (API olmayan) yakalar:
    1. Dosya ise (path içinde . varsa) ve diskte varsa -> Direkt sunar.
    2. Değilse -> index.html döndürür (Client-side routing için).
    """
    # API isteklerini pas geç (router handle etmediyse 404 dönmeli)
    # Router'lar yukarıda tanımlandığı için buraya sadece eşleşmeyenler düşer.
    if path.startswith("api/") or path == "api":
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    # Dosya sunumu denemesi
    file_path = UI_DIR / path
    if path and "." in path and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # SPA Fallback -> index.html
    index_path = UI_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

    return HTMLResponse(
        "<h1>Mami AI - Bakım Modu</h1><p>UI build dosyaları (ui-new/dist) bulunamadı. Lütfen 'npm run build' çalıştırın.</p>",
        status_code=503,
    )
# reload

# reload_15
# reload_final
# reload_live_trace
# reload_live_trace_2
# reload_live_trace_3
# Trigger reload
