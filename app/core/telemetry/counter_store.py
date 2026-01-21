import logging
from typing import Optional, Dict

from app.core.redis_client import get_redis

logger = logging.getLogger("atlas.counter_store")

_PREFIX = "atlas:snapshot"


async def _incr(key: str, reason: Optional[str] = None) -> None:
    """
    Atomik Redis sayaç artışı. Redis yoksa sessizce geçer.
    """
    try:
        client = await get_redis()
        if not client:
            return
        redis_key = f"{_PREFIX}:{key}"
        if reason:
            redis_key = f"{redis_key}:{reason}"
        await client.incr(redis_key)
    except Exception as exc:
        logger.warning(f"[CounterStore] incr failed for {key} ({reason}): {exc}")


async def _read(key: str) -> int:
    try:
        client = await get_redis()
    except Exception as exc:
        logger.warning(f"[CounterStore] get_redis failed for {key}: {exc}")
        return 0
    if not client:
        return 0
    try:
        val = await client.get(f"{_PREFIX}:{key}")
        return int(val) if val is not None else 0
    except Exception as exc:
        logger.warning(f"[CounterStore] read failed for {key}: {exc}")
        return 0


async def _read_fallback_reasons() -> Dict[str, int]:
    try:
        client = await get_redis()
    except Exception as exc:
        logger.warning(f"[CounterStore] get_redis failed for fallback: {exc}")
        client = None
    if not client:
        return {}
    prefix = f"{_PREFIX}:fallback"
    try:
        keys = await client.keys(f"{prefix}:*")
        out: Dict[str, int] = {}
        for k in keys:
            try:
                raw = await client.get(k)
                count = int(raw) if raw else 0
            except Exception:
                count = 0
            key_str = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
            reason = key_str.split(":", maxsplit=3)[-1]
            out[reason] = count
        return out
    except Exception as exc:
        logger.warning(f"[CounterStore] read fallback reasons failed: {exc}")
        return {}


async def incr_request_try() -> None:
    await _incr("requests:try")


async def incr_request_returned() -> None:
    await _incr("requests:returned")


async def incr_rollout_in() -> None:
    await _incr("requests:rollout_in")


async def incr_rag_used() -> None:
    await _incr("rag:used")


async def incr_fallback(reason: str) -> None:
    await _incr("fallback", reason=reason)


async def read_counters() -> Dict[str, int]:
    """
    Tüm zorunlu sayaçları oku (fail-open).
    """
    return {
        "requests.try": await _read("requests:try"),
        "requests.returned": await _read("requests:returned"),
        "requests.rollout_in": await _read("requests:rollout_in"),
        "rag.used": await _read("rag:used"),
    }


async def read_fallback_reasons() -> Dict[str, int]:
    return await _read_fallback_reasons()
