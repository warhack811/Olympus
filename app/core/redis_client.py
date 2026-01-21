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
# GLOBAL SINGLETON STATE (LOOP-AWARE)
# =============================================================================

# Event loop'lar arasında çakışmayı önlemek için her loop için ayrı state tutuyoruz.
# (Bkz: Future attached to a different loop hatası)
_loop_states: dict[int, dict[str, Any]] = {}

def _get_loop_state() -> dict[str, Any]:
    """Geçerli event loop için state döner."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Loop yoksa (örn. sync context), dummy bir state dönebiliriz 
        # ama bu sistemde hep asenkron bekliyoruz.
        return {"client": None, "healthy": False, "lock": None}
        
    loop_id = id(loop)
    if loop_id not in _loop_states:
        _loop_states[loop_id] = {
            "client": None,
            "healthy": False,
            "lock": asyncio.Lock()
        }
    return _loop_states[loop_id]


# =============================================================================
# PUBLIC API
# =============================================================================

async def get_redis() -> Any:
    """
    Redis async client'ı döndürür (Loop-aware Singleton).
    
    Redis bağlantısı yoksa veya başarısızsa None döner.
    Bu sayede sistem fail-soft çalışır.
    
    Returns:
        redis.asyncio.Redis | None: Redis client veya None
        
    Example:
        >>> client = await get_redis()
        >>> if client:
        ...     await client.set("key", "value")
    """
    if not REDIS_AVAILABLE:
        return None
        
    state = _get_loop_state()
    if state["lock"] is None: # Should not happen if _get_loop_state initializes it
        return None
        
    async with state["lock"]:
        if state["client"] is not None and state["healthy"]:
            return state["client"]
            
        # Yeni bağlantı oluştur
        try:
            from app.config import get_settings
            settings = get_settings()
            redis_url = settings.REDIS_URL
            
            # Connection pool ile client oluştur (her loop için kendi pool'u)
            # FIX: ssl_cert_reqs hatasını önlemek için kwarg'ları temizle
            connection_kwargs = {
                "socket_timeout": 5.0,
                "socket_connect_timeout": 5.0,
                "retry_on_timeout": True,
                "health_check_interval": 30,
                "ssl_cert_reqs": None,  # Upstash fix
            }
            
            # Eğer URL'de ssl_cert_reqs varsa temizle veya düzgün geçir
            if "ssl_cert_reqs" in redis_url:
                 # Basit çözüm: URL'den parametreyi temizlemek yerine, 
                 # ssl_cert_reqs'i burada none olarak geçebiliriz ama 
                 # en güvenlisi bu parametreyi connection_kwargs'a eklememek veya
                 # connection_class tarafından desteklenmiyorsa süzmek.
                 pass

            client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                **connection_kwargs
            )
            
            # Bağlantı testi
            await client.ping()
            state["client"] = client
            state["healthy"] = True
            logger.info(f"[REDIS] Bağlantı başarılı (Loop {id(asyncio.get_running_loop())}): {redis_url}")
            return client
            
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(f"[REDIS] Bağlantı hatası: {e}. Working Memory devre dışı.")
            state["client"] = None
            state["healthy"] = False
            return None
        except Exception as e:
            logger.error(f"[REDIS] Beklenmeyen hata: {e}. Working Memory devre dışı.")
            state["client"] = None
            state["healthy"] = False
            return None


async def close_redis() -> None:
    """
    Tüm loop'lardaki Redis bağlantılarını kapatır.
    
    Uygulama kapanırken çağrılmalı (graceful shutdown).
    """
    global _loop_states
    
    for loop_id, state in list(_loop_states.items()): # Iterate over a copy to allow modification
        client = state.get("client")
        if client:
            try:
                await client.close()
                logger.info(f"[REDIS] Bağlantı kapatıldı (Loop {loop_id}).")
            except Exception as e:
                logger.warning(f"[REDIS] Kapatma hatası (Loop {loop_id}): {e}")
        state["client"] = None
        state["healthy"] = False
    
    _loop_states.clear()


async def is_redis_healthy() -> bool:
    """
    Geçerli loop'taki Redis bağlantı durumunu kontrol eder.
    
    Health check endpoint'leri için kullanılır.
    
    Returns:
        bool: Bağlantı sağlıklı ise True
    """
    state = _get_loop_state()
    client = state.get("client")
    
    if not REDIS_AVAILABLE or client is None:
        return False
        
    try:
        await client.ping()
        state["healthy"] = True
        return True
    except Exception:
        state["healthy"] = False
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
