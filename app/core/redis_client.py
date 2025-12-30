# app/core/redis_client.py
"""
Redis Async Client - Working Memory için Singleton Bağlantı Yönetimi

Blueprint v1 Section 8 uyumlu:
- Async/await desteği (redis-py 5.x built-in)
- Singleton pattern (tek bağlantı)
- Fail-soft: Redis yoksa None döner, sistem çökmez
- Health check endpoint desteği
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger("orchestrator.redis")

# Redis kütüphanesi - lazy import (yoksa çökmez)
try:
    import redis.asyncio as aioredis
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError
    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None  # type: ignore
    RedisConnectionError = Exception  # type: ignore
    RedisTimeoutError = Exception  # type: ignore
    REDIS_AVAILABLE = False
    logger.warning("[REDIS] redis-py kütüphanesi bulunamadı. Working Memory devre dışı.")


# =============================================================================
# GLOBAL SINGLETON STATE
# =============================================================================

_redis_client: Any = None
_connection_healthy: bool = False
_lock = asyncio.Lock()


# =============================================================================
# PUBLIC API
# =============================================================================

async def get_redis() -> Any:
    """
    Redis async client'ı döndürür (Singleton).
    
    Redis bağlantısı yoksa veya başarısızsa None döner.
    Bu sayede sistem fail-soft çalışır.
    
    Returns:
        redis.asyncio.Redis | None: Redis client veya None
        
    Example:
        >>> client = await get_redis()
        >>> if client:
        ...     await client.set("key", "value")
    """
    global _redis_client, _connection_healthy
    
    if not REDIS_AVAILABLE:
        return None
        
    async with _lock:
        if _redis_client is not None and _connection_healthy:
            return _redis_client
            
        # Yeni bağlantı oluştur
        try:
            from app.config import get_settings
            settings = get_settings()
            redis_url = settings.REDIS_URL
            
            # Connection pool ile client oluştur
            _redis_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,       # Okuma timeout
                socket_connect_timeout=5.0,  # Bağlantı timeout
                retry_on_timeout=True,
                health_check_interval=30,  # 30s'de bir health check
            )
            
            # Bağlantı testi
            await _redis_client.ping()
            _connection_healthy = True
            logger.info(f"[REDIS] Bağlantı başarılı: {redis_url}")
            return _redis_client
            
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"[REDIS] Bağlantı hatası: {e}. Working Memory devre dışı.")
            _redis_client = None
            _connection_healthy = False
            return None
        except Exception as e:
            logger.error(f"[REDIS] Beklenmeyen hata: {e}. Working Memory devre dışı.")
            _redis_client = None
            _connection_healthy = False
            return None


async def close_redis() -> None:
    """
    Redis bağlantısını kapatır.
    
    Uygulama kapanırken çağrılmalı (graceful shutdown).
    """
    global _redis_client, _connection_healthy
    
    async with _lock:
        if _redis_client is not None:
            try:
                await _redis_client.close()
                logger.info("[REDIS] Bağlantı kapatıldı.")
            except Exception as e:
                logger.warning(f"[REDIS] Kapatma hatası: {e}")
            finally:
                _redis_client = None
                _connection_healthy = False


async def is_redis_healthy() -> bool:
    """
    Redis bağlantı durumunu kontrol eder.
    
    Health check endpoint'leri için kullanılır.
    
    Returns:
        bool: Bağlantı sağlıklı ise True
    """
    global _connection_healthy
    
    if not REDIS_AVAILABLE or _redis_client is None:
        return False
        
    try:
        await _redis_client.ping()
        _connection_healthy = True
        return True
    except Exception:
        _connection_healthy = False
        return False


async def get_redis_info() -> dict[str, Any]:
    """
    Redis sunucu bilgilerini döndürür (debug/admin için).
    
    Returns:
        dict: Redis bilgileri veya boş dict
    """
    if not REDIS_AVAILABLE:
        return {"available": False, "reason": "redis-py not installed"}
        
    client = await get_redis()
    if client is None:
        return {"available": False, "reason": "connection failed"}
        
    try:
        info = await client.info(section="server")
        memory_info = await client.info(section="memory")
        
        return {
            "available": True,
            "version": info.get("redis_version", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
            "used_memory_human": memory_info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_redis_available() -> bool:
    """
    Redis kütüphanesi yüklü mü? (Sync check)
    
    Lazy import veya dependency check için kullanılır.
    """
    return REDIS_AVAILABLE
