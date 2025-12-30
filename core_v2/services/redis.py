import redis.asyncio as redis
from core_v2.config.settings import settings
import logging
from typing import Optional, Any

logger = logging.getLogger("core_v2.services.redis")

class RedisService:
    """
    Singleton Async Redis Service with Cloud Support (Upstash/Render).
    Implements 'Fail-open' logic: If Redis is down, methods return None/False instead of crashing.
    """
    _instance: Optional["RedisService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._client: Optional[redis.Redis] = None
        self._initialized = True

    async def connect(self) -> None:
        """Initializes the Redis connection pool."""
        if self._client:
            return

        try:
            kwargs = {
                "encoding": "utf-8",
                "decode_responses": True,
                "socket_timeout": 5.0,
                # "retry_on_timeout": True # Removed to keep kwargs simple as per request, relying on defaults or re-adding if needed carefully
            }
            
            # Simple SSL configuration for Upstash/Cloud
            if settings.REDIS_URL.startswith("rediss://"):
                kwargs["ssl_cert_reqs"] = "none"

            self._client = redis.from_url(settings.REDIS_URL, **kwargs)
            
            # Connection Test
            await self._client.ping()
            logger.info(f"✅ Redis connected: {settings.REDIS_URL.split('@')[-1]}")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}. Proceeding without Cache (Fail-Open).")
            self._client = None

    async def disconnect(self) -> None:
        """Closes the connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis disconnected.")

    @property
    def client(self) -> Optional[redis.Redis]:
        """Returns the raw client if connected, else None."""
        return self._client
    
    # --- Helper methods for Fail-Safe Operations ---

    async def get(self, key: str) -> Optional[str]:
        if not self._client: return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis GET failed for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ex: int = None) -> bool:
        if not self._client: return False
        try:
            return await self._client.set(key, value, ex=ex)
        except Exception as e:
            logger.warning(f"Redis SET failed for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self._client: return False
        try:
           return await self._client.delete(key)
        except Exception as e:
            logger.warning(f"Redis DELETE failed for {key}: {e}")
            return False
            
    async def incr(self, key: str) -> Optional[int]:
        if not self._client: return None
        try:
            return await self._client.incr(key)
        except Exception as e:
            logger.warning(f"Redis INCR failed for {key}: {e}")
            return None
    
    async def expire(self, key: str, time: int) -> bool:
        if not self._client: return False
        try:
            return await self._client.expire(key, time)
        except Exception as e:
            logger.warning(f"Redis EXPIRE failed for {key}: {e}")
            return False

# Global instance
redis_service = RedisService()
