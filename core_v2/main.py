from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from core_v2.config.settings import settings
from core_v2.services.redis import redis_service
from core_v2.services.graph_db import graph_service
from core_v2.api.dependencies import RedisDep, GraphDep
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("core_v2.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle:
    1. Connect services on startup
    2. Close connections on shutdown
    """
    logger.info("🚀 Starting Mami AI Core v2...")
    
    # Startup
    await redis_service.connect()
    # Graph service connects in init, but we can verify or explicitly connect if changed pattern
    # graph_service is singleton and auto-connects in __init__ currently, 
    # but strictly speaking async init is better. For now, it works as implemented.
    if not graph_service._driver:
       logger.warning("Graph service not connected, retrying...")
       graph_service.connect()

    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    await redis_service.disconnect()
    graph_service.close()

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware (Allow All for Development/MVP)
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
    expose_headers=["X-Conversation-ID"],
)

# FALLBACK: Import Legacy Routers to keep system running
try:
    from app.api.auth_routes import router as auth_router
    from app.api.routes.chat import router as chat_router
    from app.api.routes.memories import router as memories_router
    from app.api.routes.documents import router as documents_router
    from app.api.routes.images import router as images_router
    from app.api.routes.preferences import router as preferences_router
    
    # Include Legacy Routers under /api/v1 prefix
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["v1-auth"])
    app.include_router(chat_router, prefix="/api/v1/user", tags=["v1-chat"])
    app.include_router(memories_router, prefix="/api/v1/user", tags=["v1-memories"])
    app.include_router(documents_router, prefix="/api/v1/user", tags=["v1-documents"])
    app.include_router(images_router, prefix="/api/v1/user", tags=["v1-images"])
    app.include_router(preferences_router, prefix="/api/v1/user", tags=["v1-preferences"])
    
    logger.info("✅ Legacy Routers (V1) successfully mounted on Core V2")
except ImportError as e:
    logger.error(f"❌ Failed to import legacy routers: {e}")

@app.get("/health")
async def health_check():
    """Simple health check for Render/K8s Probes."""
    return {
        "status": "ok",
        "version": "core_v2",
        "env": settings.APP_ENV,
        "service": "Mami AI v4"
    }

@app.get("/api/v2/test-db")
async def test_db_connectivity(
    redis: RedisDep,
    graph: GraphDep
):
    """
    Diagnostic endpoint to verify connectivity to Redis and Neo4j.
    """
    results = {
        "redis": "unknown",
        "neo4j": "unknown"
    }
    
    # 1. Test Redis
    try:
        if redis.client:
            await redis.set("test_ping", "pong", ex=10)
            val = await redis.get("test_ping")
            results["redis"] = "connected" if val == "pong" else "write_failed"
        else:
            results["redis"] = "disconnected"
    except Exception as e:
        results["redis"] = f"error: {str(e)}"

    # 2. Test Neo4j
    try:
        if graph._driver:
            with graph._driver.session() as session:
                res = session.run("RETURN 1 as val").single()
                if res and res["val"] == 1:
                     results["neo4j"] = "connected"
                else:
                     results["neo4j"] = "query_failed"
        else:
            results["neo4j"] = "disconnected"
    except Exception as e:
        results["neo4j"] = f"error: {str(e)}"

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core_v2.main:app", host="0.0.0.0", port=8000, reload=True)
