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
    Manages API keys with rate-limiting & fatal error awareness.
    """
    
    def __init__(self, keys: List[str] = None):
        self._keys = keys or list(settings.GROQ_API_KEYS) # Make a copy to allow modification
        self._lock = asyncio.Lock()
        self._local_index = 0
        
        # RAM Fallback State (used when Redis is down or for fatal blocks)
        self._memory_cooldowns: Dict[str, float] = {}
        
        # Redis Key Prefix
        self._redis_prefix = "key_manager:groq"
        self._cooldown_seconds = 60  # Default cooldown for RPM limit

        if not self._keys:
            logger.warning("⚠️ No GROQ_API_KEYS configured! KeyManager will fail requests.")

    async def get_next_key(self) -> str:
        """
        Retrieves the next available key using Hybrid Logic.
        """
        if not self._keys:
            raise ResourceExhausted("No API keys configured or all were removed.")

        async with self._lock:
            # Atomic Round-Robin
            start_index = self._local_index
            self._local_index = (self._local_index + 1) % len(self._keys)
            
            for i in range(len(self._keys)):
                current_idx = (start_index + i) % len(self._keys)
                key = self._keys[current_idx]
                
                # Health Check
                if await self._is_key_healthy(key):
                    return key

        raise ResourceExhausted("All keys are currently in cooldown or exhausted.")

    async def _is_key_healthy(self, key: str) -> bool:
        """Checks if key is healthy using Redis (priority) or Memory."""
        
        # 1. Check Memory Cooldowns first (Fastest reject)
        if not self._check_memory_health(key):
            return False

        # 2. Check Redis Cooldowns (Distributed reject)
        if redis_service.client:
            cooldown_key = f"{self._redis_prefix}:{key[-4:]}:cooldown"
            is_cooldown = await redis_service.get(cooldown_key)
            if is_cooldown:
                return False
        
        return True

    def _check_memory_health(self, key: str) -> bool:
        """Returns True if key is HEALTHY in Memory."""
        import time
        now = time.time()
        
        if key in self._memory_cooldowns:
            if self._memory_cooldowns[key] > now:
                return False 
            else:
                del self._memory_cooldowns[key]
        return True

    async def report_failure(self, key: str, is_fatal: bool = False):
        """
        Handles key failure.
        - is_fatal=True (401): Remove key permanently.
        - is_fatal=False (429): Cooldown key for 60s.
        """
        safe_key = key[-4:]
        
        async with self._lock:
            if is_fatal:
                logger.error(f"⛔ Key ...{safe_key} is Invalid/Revoked (401). Removing permanently.")
                if key in self._keys:
                    self._keys.remove(key)
                    # Reset index to avoid out of bounds
                    if self._local_index >= len(self._keys):
                        self._local_index = 0
            else:
                logger.warning(f"⚠️ Key ...{safe_key} Rate Limited (429). Cooling down for {self._cooldown_seconds}s.")
                
                # 1. Update Redis
                if redis_service.client:
                    cooldown_key = f"{self._redis_prefix}:{safe_key}:cooldown"
                    await redis_service.set(cooldown_key, "1", ex=self._cooldown_seconds)
                
                # 2. Update Memory
                import time
                self._memory_cooldowns[key] = time.time() + self._cooldown_seconds

# --- Verification Script ---
if __name__ == "__main__":
    import asyncio
    import sys

    # Configure logging to stdout
    logging.basicConfig(level=logging.INFO)

    async def test_key_manager():
        print("\n🧪 STARTING KEY MANAGER HYBRID TEST (Refined)")
        print("="*50)
        
        # 1. Setup Mock Environment
        mock_keys = ["sk-A", "sk-B", "sk-C"]
        settings.GROQ_API_KEYS = mock_keys # Mock override
        
        print(f"1. Initializing Services with {len(mock_keys)} keys...")
        await redis_service.connect()
        
        manager = KeyManager(mock_keys)
        
        status_msg = "BAĞLI (Redis Modu)" if redis_service.client else "BAĞLI DEĞİL (RAM Modu)"
        print(f"   Redis Durumu: {status_msg}")

        # 2. Request Keys Loop
        print("\n2. Requesting 5 Keys...")
        failed_key_429 = None
        
        for i in range(5):
            try:
                k = await manager.get_next_key()
                print(f"   Req {i+1}: ...{k[-4:]}")
                
                # Scenario: Key B gets 429
                if k.endswith("sk-B") and failed_key_429 is None:
                    print(f"      ⚠️ Simulating 429 on ...{k[-4:]}")
                    await manager.report_failure(k, is_fatal=False)
                    failed_key_429 = k

            except ResourceExhausted:
                print("   ⛔ Resource Exhausted!")

        # 3. Verify Fatal Error Logic
        print("\n3. Testing Fatal Error (401)...")
        try:
            # Let's revoke 'sk-C'
            k_fatal = "sk-C" 
            print(f"   ⛔ Simulating 401 on ...{k_fatal[-4:]}")
            await manager.report_failure(k_fatal, is_fatal=True)
            
            # Check remaining keys
            remaining = manager._keys
            print(f"   Remaining Keys: {len(remaining)} -> {[k[-4:] for k in remaining]}")
            assert k_fatal not in remaining
            print("   ✅ Assertion Passed: Unknown/Fatal key removed.")
            
        except Exception as e:
            print(f"   ❌ Test Failed: {e}")

        await redis_service.disconnect()
        print("\n✅ TEST COMPLETED")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_key_manager())
