from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from core_v2.config.settings import Settings, settings
from core_v2.services.redis import RedisService, redis_service
from core_v2.services.key_manager import KeyManager
from core_v2.services.graph_db import GraphService, graph_service

# Global KeyManager instance
_key_manager_instance = None

@lru_cache()
def get_settings() -> Settings:
    """Returns the cached settings instance."""
    return settings

@lru_cache()
def get_redis_service() -> RedisService:
    """Returns the singleton Redis Service."""
    return redis_service

@lru_cache()
def get_graph_service() -> GraphService:
    """Returns the singleton Graph Service."""
    return graph_service

async def get_key_manager() -> KeyManager:
    """
    Returns the Key Manager singleton.
    Ensure strict Singleton implementation for state consistency.
    """
    global _key_manager_instance
    if _key_manager_instance is None:
        _key_manager_instance = KeyManager()
    return _key_manager_instance

# Type Aliases
SettingsDep = Annotated[Settings, Depends(get_settings)]
RedisDep = Annotated[RedisService, Depends(get_redis_service)]
GraphDep = Annotated[GraphService, Depends(get_graph_service)]
KeyManagerDep = Annotated[KeyManager, Depends(get_key_manager)]
