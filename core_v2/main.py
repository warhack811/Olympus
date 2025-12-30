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
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None
)

# CORS Middleware (Allow All for Development/MVP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
