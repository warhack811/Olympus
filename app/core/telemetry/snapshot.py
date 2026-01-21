import logging
from typing import Any, Dict

from app.config import get_settings
from app.core.telemetry import counter_store
from app.core.telemetry.context import get_trace_id

logger = logging.getLogger("atlas.snapshot")


async def build_admin_orch_snapshot(verbose: bool = False) -> Dict[str, Any]:
    """
    OrchDebugPanel contract'ına uyan snapshot.
    Fail-open: Redis hatasında tüm sayaçlar 0/map empty.
    """
    settings = get_settings()
    # Counters (fail-open)
    counters = await counter_store.read_counters()
    fallback_reasons = await counter_store.read_fallback_reasons()

    flags = {
        "production_enabled": getattr(settings, "ATLAS_ENABLED", True),
        "streaming_enabled": True,
        "rollout_percent": getattr(settings, "ATLAS_ROLLOUT_PERCENT", 100),
        "allowlist_count": len(getattr(settings, "ATLAS_ROLLOUT_ALLOWLIST", []) or []),
    }

    snapshot = {
        "flags": flags,
        "rollout": flags,
        "telemetry_summary": {
            "requests": {
                "try": counters.get("requests.try", 0),
                "returned": counters.get("requests.returned", 0),
                "rollout_in": counters.get("requests.rollout_in", 0),
            },
            "rag": {"used": counters.get("rag.used", 0)},
            "fallback_reasons": fallback_reasons,
        },
        "last_trace_summary": {
            "trace_id": get_trace_id(),
            "event_count": 0,
            "timestamp": None,
        },
        "runtime_state": {},
        "auto_circuit": {"status": "not_implemented"},
    }

    return {
        "snapshot": snapshot,
        "telemetry": {},
        "verbose": verbose,
    }
