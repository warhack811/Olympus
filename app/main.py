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
from app.core.logger import get_logger, log_request, log_response
from app.memory.conversation import set_user_resolver as set_conv_user_resolver
from app.memory.store import set_user_resolver as set_memory_user_resolver

# =============================================================================
# YAPILANDIRMA
# =============================================================================

settings = get_settings()
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
# FASTAPI UYGULAMASI
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="Mami AI - Gelişmiş AI Asistan",
    version="4.2.0",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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


# Basit istek loglamasi (mami.log ve console)
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = perf_counter()
    user = None
    try:
        user = get_username_from_request(request)
    except Exception:
        pass

    log_request(logger, request.method, request.url.path, user=user)
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - start) * 1000
        logger.error(f"[RESPONSE] status=500 duration={duration_ms:.2f}ms path={request.url.path}")
        raise
    duration_ms = (perf_counter() - start) * 1000
    log_response(logger, response.status_code, duration_ms, extra={"path": request.url.path})
    return response


# =============================================================================
# STATİK DOSYALAR
# =============================================================================

BASE_DIR = project_root
# UI_DIR artık yeni React build çıktısını (dist) gösteriyor
UI_DIR = BASE_DIR / "ui-new" / "dist"
IMAGES_DIR = BASE_DIR / "data" / "images"

# Dizinleri oluştur
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
# /assets -> Vite tarafından üretilen JS/CSS dosyaları
if (UI_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(UI_DIR / "assets")), name="assets")

# /images -> Kullanıcı yüklemeleri
app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")

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
# LIFECYCLE EVENTS
# =============================================================================


@app.on_event("startup")
async def on_startup():
    """Uygulama başlangıcında çalışır."""
    logger.info("=" * 50)
    logger.info("Mami AI v4.2 (New UI) başlatılıyor...")
    logger.info("=" * 50)

    # 1. Veritabanı ve varsayılan config'leri yükle
    init_database_with_defaults()

    # 2. Varsayılan admin oluştur
    ensure_default_admin()

    # 3. İlk davet kodunu oluştur
    invite = ensure_initial_invite()
    logger.info(f"Test için davet kodu: {invite.code}")

    # 4. Bakım görevlerini başlat
    try:
        from app.core.maintenance import start_maintenance_scheduler

        start_maintenance_scheduler()
    except ImportError:
        pass

    try:
        from app.core.dynamic_config import config_service

        config_service.get_category("system")
    except Exception:
        pass

    # 5. RAG v2 FTS tablosunu başlat
    try:
        from app.memory.rag_v2_lexical import init_fts

        init_fts()
        logger.info("RAG v2 FTS tablosu hazır.")
    except Exception as e:
        logger.warning(f"RAG v2 FTS init hatası: {e}")

    logger.info("Mami AI hazır!")


@app.on_event("shutdown")
async def on_shutdown():
    """Uygulama kapanırken çalışır."""
    logger.info("Mami AI kapatılıyor...")


# =============================================================================
# WEBSOCKET
# =============================================================================

from http.cookies import SimpleCookie

from app.auth.dependencies import SESSION_COOKIE_NAME
from app.auth.session import get_user_from_session_token

# WebSocket bağlantıları - websocket_sender.py ile aynı isim olmalı!
from app.core.websockets import connected


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket bağlantı endpoint'i - username ile kayıt yapar."""
    await ws.accept()

    # Cookie'den session token al ve kullanıcı bul
    username = "anonymous"
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
        logger.info(f"[WEBSOCKET] Cookie token: {token[:20] if token else 'None'}...")

        if token:
            user = get_user_from_session_token(token)
            if user:
                username = user.username
                logger.info(f"[WEBSOCKET] User resolved: {username}")
    except Exception as e:
        logger.error(f"[WEBSOCKET] Username alınamadı: {e}")

    # Dict olarak kaydet: {ws: username}
    connected[ws] = username
    logger.info(
        f"[WEBSOCKET] Yeni bağlantı: {username}, toplam: {len(connected)}, all_users: {list(connected.values())}"
    )

    try:
        while True:
            await ws.receive_text()
    except Exception as e:
        logger.debug(f"[WEBSOCKET] Bağlantı kapandı ({username}): {e}")
    finally:
        if ws in connected:
            del connected[ws]
        logger.info(f"[WEBSOCKET] Bağlantı kaldırıldı: {username}, kalan: {len(connected)}")


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
from app.api.routes import chat, documents, images, memories, preferences

# API v1 (Yeni standart yol)
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["v1-auth"])
app.include_router(public_routes.router, prefix="/api/v1/public", tags=["v1-public"])
# app.include_router(user_routes.router, prefix="/api/v1/user", tags=["v1-user"])  # DEPRECATED
app.include_router(chat.router, prefix="/api/v1/user", tags=["v1-chat"])
app.include_router(memories.router, prefix="/api/v1/user", tags=["v1-memories"])
app.include_router(documents.router, prefix="/api/v1/user", tags=["v1-documents"])
app.include_router(images.router, prefix="/api/v1/user", tags=["v1-images"])
app.include_router(preferences.router, prefix="/api/v1/user", tags=["v1-preferences"])
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
