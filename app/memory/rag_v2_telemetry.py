import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

TELEMETRY_FILE = os.path.join("data", "rag_v2_telemetry.jsonl")


@dataclass
class RAGV2Stats:
    query_hash: str
    owner: str
    scope: str
    mode_used: str = "unknown"
    used_lexical: bool = False
    dense_count: int = 0
    lexical_count: int = 0
    merged_count: int = 0
    best_score_type: str | None = None
    best_score: float | None = None
    second_score: float | None = None
    gating_result: str = "unknown"  # "pass"|"threshold"|"margin"|"empty"|"exception"
    marker_written: bool = False
    bypass_used: bool = False
    lexical_sanity_pass: bool = False
    latency_ms_total: int = 0
    latency_ms_dense: int = 0
    latency_ms_lexical: int = 0
    latency_ms_merge: int = 0
    timestamp: str = ""
    deep_fallback_triggered: bool = False
    expansion_used: bool = False
    docs_total: int = 0
    docs_selected: int = 0
    doc_selection_used: bool = False
    conversation_pinning_used: bool = False
    continue_mode_used: bool = False
    continuation_window_pages: int = 0
    last_page_used: int | None = None
    page_window_applied: bool = False


def calculate_query_hash(query: str) -> str:
    try:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:8]
    except Exception:
        return "hash_error"


def log_stats(stats: RAGV2Stats) -> None:
    """Log stats to JSONL file (Fail-open)."""
    try:
        if not stats.timestamp:
            stats.timestamp = datetime.utcnow().isoformat()

        base_dir = Path(__file__).resolve().parents[2]
        path = base_dir / "data" / "rag_v2_telemetry.jsonl"

        logger.info(f"[RAG_V2_TELEMETRY] write_start path={path}")

        path.parent.mkdir(parents=True, exist_ok=True)

        line = json.dumps(asdict(stats)) + "\n"

        with open(path, "a", encoding="utf-8") as f:
            f.write(line)

        logger.info(f"[RAG_V2_TELEMETRY] write_ok bytes={len(line)}")

    except Exception:
        logger.exception("[RAG_V2_TELEMETRY] write_failed")
