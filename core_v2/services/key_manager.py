import asyncio
import logging
from typing import List, Dict, Optional
from core_v2.config.settings import settings
from core_v2.services.redis import redis_service

logger = logging.getLogger("core_v2.services.key_manager")

class ResourceExhausted(Exception):
    """Raised when all keys are in cooldown/exhausted."""
    pass

class KeyManager:
    """
    Hybrid Key Rotation System (Redis + Memory Fallback).
    Manages API keys with rate-limiting awareness.
    """
    
    def __init__(self, keys: List[str] = None):
        self._keys = keys or settings.GROQ_API_KEYS
        self._lock = asyncio.Lock()
        self._index = 0  # Round Robin Cursor
        
        # RAM Fallback State (used when Redis is down)
        # Structure: {key: expiry_timestamp}
        self._memory_cooldowns: Dict[str, float] = {}
        
        # Redis Key Prefix
        self._redis_prefix = "key_manager:groq"
        self._cooldown_seconds = 60  # Default cooldown for RPM limit

        if not self._keys:
            logger.warning("⚠️ No GROQ_API_KEYS configured! KeyManager will fail requests.")

    async def get_next_key(self) -> str:
        """
        Retrieves the next available key using Round-Robin + Health Check.
        """
        if not self._keys:
            raise ResourceExhausted("No API keys configured.")

        async with self._lock:
            start_index = self._index
            # Rotate cursor for the *next* caller immediately
            self._index = (self._index + 1) % len(self._keys)
            
            # Iterate through keys starting from start_index
            for i in range(len(self._keys)):
                current_idx = (start_index + i) % len(self._keys)
                key = self._keys[current_idx]
                
                # Check health (Redis -> RAM)
                if redis_service.client:
                    if await self._check_redis_health(key):
                        return key
                else:
                    if self._check_memory_health(key):
                        return key

        raise ResourceExhausted("All keys are currently in cooldown.")

    async def _check_redis_health(self, key: str) -> bool:
        """Returns True if key is HEALTHY (not in cooldown)."""
        cooldown_key = f"{self._redis_prefix}:{key[-4:]}:cooldown"
        is_cooldown = await redis_service.get(cooldown_key)
        return not is_cooldown

    def _check_memory_health(self, key: str) -> bool:
        """Returns True if key is HEALTHY (not in cooldown)."""
        import time
        now = time.time()
        
        # Lazy cleanup (optimization: don't cleanup whole dict every time, just check key)
        if key in self._memory_cooldowns:
            if self._memory_cooldowns[key] > now:
                return False # Still in cooldown
            else:
                del self._memory_cooldowns[key] # Expired
        return True

    async def report_failure(self, key: str):
        """
        Marks a key as failed/exhausted, putting it into cooldown.
        """
        safe_key = key[-4:]
        logger.warning(f"Key ...{safe_key} failed. Triggering cooldown.")
        
        async with self._lock:
            # 1. Update Redis
            if redis_service.client:
                cooldown_key = f"{self._redis_prefix}:{safe_key}:cooldown"
                await redis_service.set(cooldown_key, "1", ex=self._cooldown_seconds)
            
            # 2. Update Memory
            import time
            self._memory_cooldowns[key] = time.time() + self._cooldown_seconds

# --- Verification Script (Run directly to test) ---
if __name__ == "__main__":
    import asyncio
    import sys

    async def test_key_manager():
        print("\n🧪 STARTING KEY MANAGER HYBRID TEST")
        print("="*40)
        
        # 1. Setup Mock Environment
        mock_keys = ["sk-key1", "sk-key2", "sk-key3"]
        settings.GROQ_API_KEYS = mock_keys
        
        print("1. Initializing Services...")
        await redis_service.connect()
        
        manager = KeyManager(mock_keys)
        
        if redis_service.client:
            print("   ✅ Redis Mode Active")
        else:
            print("   ⚠️ Redis Connection Failed -> Running in RAM Fallback Mode")

        # 2. Request Keys Loop
        failed_key = None
        print("\n2. Requesting Keys (Round-Robin simulation)...")
        for i in range(5):
            try:
                k = await manager.get_next_key()
                print(f"   Request {i+1}: Got Key ...{k[-4:]}")
                
                # Simulate a failure on the second request
                if i == 1:
                    print(f"   ❌ Reporting Failure for ...{k[-4:]}")
                    await manager.report_failure(k)
                    failed_key = k
                    
            except ResourceExhausted:
                print("   ⛔ Resource Exhausted!")

        # 3. Check Status
        print(f"\n3. Verifying Cooldown Logic for Failed Key: ...{failed_key[-4:]}")
        try:
             # We expect the failed key to be skipped in the next few calls
             # Check next 3 calls to be safe
             for _ in range(3):
                 k = await manager.get_next_key()
                 print(f"   Next key: ...{k[-4:]}")
                 assert k != failed_key, f"❌ Test Failed: Triggered key {failed_key} was returned!"
             
             print("   ✅ Validated: Failed key was skipped.")
        except ResourceExhausted:
             print("   ⚠️ Resource Exhausted (All keys failed?)")

        await redis_service.disconnect()
        print("\n✅ TEST COMPLETED")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_key_manager())
