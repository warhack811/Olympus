import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# In-memory store: {conversation_id: {"upload_id": str, "timestamp": float}}
# In a real production system, use Redis.
_PIN_STORE: dict[str, dict[str, Any]] = {}

PIN_TTL_SECONDS = 3600  # 1 hour


def get_active_doc(conversation_id: str) -> str | None:
    """Get the pinned document ID for a conversation, if valid."""
    entry = _get_entry(conversation_id)
    return entry.get("upload_id") if entry else None


def get_active_page(conversation_id: str) -> int | None:
    """Get the last accessed page for a conversation."""
    entry = _get_entry(conversation_id)
    return entry.get("last_page") if entry else None


def _get_entry(conversation_id: str) -> dict[str, Any] | None:
    if not conversation_id:
        return None
    try:
        entry = _PIN_STORE.get(conversation_id)
        if not entry:
            return None
        timestamp = entry.get("timestamp", 0)
        if time.time() - timestamp > PIN_TTL_SECONDS:
            del _PIN_STORE[conversation_id]
            return None
        return entry
    except Exception as e:
        logger.warning(f"[RAG v2 Conv] Error getting entry: {e}")
        return None


def set_active_doc(conversation_id: str, upload_id: str, last_page: int | None = None) -> None:
    """
    Pin a document to a conversation or update its state.
    If upload_id is same as existing, it purely updates metadata (like last_page).
    """
    if not conversation_id or not upload_id:
        return

    try:
        existing = _PIN_STORE.get(conversation_id)

        # If updating existing pin
        if existing and existing.get("upload_id") == upload_id:
            existing["timestamp"] = time.time()  # Refresh TTL
            if last_page is not None:
                existing["last_page"] = last_page
            _PIN_STORE[conversation_id] = existing
            logger.debug(f"[RAG v2 Conv] Updated doc {upload_id} in {conversation_id}, page={last_page}")
        else:
            # New pin
            data = {
                "upload_id": upload_id,
                "timestamp": time.time(),
            }
            if last_page is not None:
                data["last_page"] = last_page
            _PIN_STORE[conversation_id] = data
            logger.debug(f"[RAG v2 Conv] Pinned doc {upload_id} to {conversation_id}, page={last_page}")

    except Exception as e:
        logger.warning(f"[RAG v2 Conv] Error setting pin: {e}")
