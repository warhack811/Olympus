"""
Mami AI - Cache Bridge
----------------------
app.core.cache modülü bulunamadığı için geçici bir köprü görevi görür.
Asıl işlemler app.core.redis_client üzerinden yürütülür.
"""

from typing import Any, Optional
from app.core.redis_client import get_redis

class RedisProxy:
    """ redis_client nesnesi gibi davranan asenkron proxy. """
    
    async def get(self, key: str) -> Any:
        client = await get_redis()
        if client:
            return await client.get(key)
        return None

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> Any:
        client = await get_redis()
        if client:
            return await client.set(key, value, ex=ex)
        return None

    async def setex(self, key: str, time: int, value: Any) -> Any:
        client = await get_redis()
        if client:
            return await client.setex(key, time, value)
        return None

    async def delete(self, *keys: str) -> Any:
        client = await get_redis()
        if client:
            return await client.delete(*keys)
        return 0

# Singleton proxy instance
redis_client = RedisProxy()
