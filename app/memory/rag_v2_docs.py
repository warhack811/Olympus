import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_doc_candidates_from_seeds(seed_candidates: list[dict[str, Any]], top_k_docs: int = 5) -> list[str]:
    """
    Select top documents from seed retrieval results.

    Args:
        seed_candidates: List of minimal candidate dicts (must have 'upload_id', 'score').
        top_k_docs: Number of unique documents to select.

    Returns:
        List of selected upload_ids.
    """
    if not seed_candidates:
        return []

    try:
        # Group by upload_id -> min_score
        best_scores = {}
        for c in seed_candidates:
            uid = c.get("upload_id")
            if not uid:
                continue

            # Use 'score' (distance). Lower is better.
            score = c.get("score", 1.0)

            if uid not in best_scores:
                best_scores[uid] = score
            else:
                best_scores[uid] = min(best_scores[uid], score)

        # Rank: Sort by score (asc)
        sorted_uploads = sorted(best_scores.keys(), key=lambda u: best_scores[u])

        # Select top K
        selected = sorted_uploads[:top_k_docs]
        return selected

    except Exception as e:
        logger.warning(f"[RAG v2 Docs] Selection failed: {e}")
        return []
