"""
Mami AI - Episode Pipeline Service (Atlas Sovereign Edition)
------------------------------------------------------------
Anı sıkıştırma ve vektör gömme servisi.

Temel Sorumluluklar:
1. Turn Özetleme: LLM ile konuşma loglarını özet haline getirme
2. Vektör Gömme: Gemini embedding ile Qdrant'a kaydetme
3. Graceful Degradation: Hata durumunda ana akışı bloklamamak
"""

import uuid
import asyncio
import random
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)


# Retry settings
EPISODE_RETRY_MAX_ATTEMPTS = 3
EPISODE_RETRY_BASE_DELAY = 1.0
EPISODE_RETRY_JITTER = 0.5


async def _retry_with_backoff(
    func,
    max_attempts: int = EPISODE_RETRY_MAX_ATTEMPTS,
    base_delay: float = EPISODE_RETRY_BASE_DELAY,
    jitter: float = EPISODE_RETRY_JITTER,
    operation_name: str = "operation"
):
    """Generic async retry with exponential backoff + jitter."""
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            if attempt == max_attempts:
                logger.error(f"{operation_name}: All {max_attempts} attempts failed: {e}")
                raise
            
            delay = (base_delay * (2 ** (attempt - 1))) + random.uniform(0, jitter)
            logger.warning(f"{operation_name}: Attempt {attempt} failed: {e}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)
    
    raise last_exception


async def summarize_turns(
    turns: List[Dict],
    llm_provider = None
) -> str:
    """
    Konuşma turn'lerini LLM ile özetler.
    
    Args:
        turns: Turn listesi [{"role": "user"|"assistant", "content": "..."}]
        llm_provider: LLM provider instance
    
    Returns:
        Özet metni
    """
    if not turns:
        return ""
    
    # Format turns for summarization
    turn_text = "\n".join([
        f"{t.get('role', 'user').upper()}: {t.get('content', '')[:500]}"
        for t in turns[:20]  # Limit to 20 turns for memory efficiency
    ])
    
    prompt = f"""Aşağıdaki konuşmayı 2-3 cümleyle özetle. Sadece özeti yaz, başka bir şey ekleme.

KONUŞMA:
{turn_text}

ÖZET:"""
    
    try:
        if llm_provider:
            summary = await llm_provider.generate(
                prompt=prompt,
                temperature=0.3
            )
            return summary.strip()[:500]  # Limit summary length
        
        # Fallback: Simple extraction
        return turn_text[:300] + "..."
        
    except Exception as e:
        logger.warning(f"[EpisodeService] Summarization error: {e}")
        return turn_text[:200] + "..."


async def finalize_episode(
    episode_id: str,
    user_id: str,
    session_id: str,
    summary: str,
    model: str = "unknown",
    graph_repo = None,
    vector_repo = None,
    embedder = None
) -> Dict[str, Any]:
    """
    Episode'u vektör gömmeleriyle sonlandır.
    
    Flow:
        1. Validate summary
        2. Generate embedding (Gemini)
        3. Upsert to Qdrant
        4. Update Neo4j metadata
    
    Args:
        episode_id: Episode identifier
        user_id: User identifier
        session_id: Session identifier
        summary: Episode summary
        model: Model used for summary
        graph_repo: Graph repository
        vector_repo: Vector repository
        embedder: Embedding service
    
    Returns:
        {"status": "success"|"partial"|"failed", "vector_status": "READY"|"FAILED"|"SKIPPED"}
    """
    result = {
        "status": "success",
        "vector_status": "SKIPPED",
        "embedding_model": None,
        "error": None
    }
    
    # Telemetry start
    telemetry.emit(
        EventType.MEMORY_OP,
        {"op": "finalize_episode", "episode_id": episode_id},
        component="episode"
    )
    
    # Validate summary
    if not summary or len(summary.strip()) < 10:
        result["vector_status"] = "SKIPPED"
        result["error"] = "Summary too short"
        logger.info(f"[EpisodeService] Episode {episode_id}: Summary too short, skipped")
        return result
    
    # Generate embedding
    embedding = None
    if embedder:
        try:
            async def _embed():
                return await embedder.embed(summary)
            
            embedding = await _retry_with_backoff(
                _embed,
                operation_name=f"Episode {episode_id} embedding"
            )
            result["embedding_model"] = "text-embedding-004"
            logger.debug(f"[EpisodeService] Episode {episode_id}: Embedding generated")
            
        except Exception as e:
            logger.warning(f"[EpisodeService] Embedding failed: {e}")
            result["vector_status"] = "FAILED"
            result["error"] = str(e)[:100]
            result["status"] = "partial"
    
    # Upsert to Qdrant
    if embedding and vector_repo:
        try:
            async def _upsert():
                return await vector_repo.upsert_episode(
                    episode_id=episode_id,
                    embedding=embedding,
                    user_id=user_id,
                    session_id=session_id,
                    text=summary
                )
            
            await _retry_with_backoff(
                _upsert,
                operation_name=f"Episode {episode_id} Qdrant"
            )
            result["vector_status"] = "READY"
            logger.info(f"[EpisodeService] Episode {episode_id}: Qdrant upsert successful")
            
        except Exception as e:
            logger.warning(f"[EpisodeService] Qdrant upsert failed (graceful): {e}")
            result["vector_status"] = "FAILED"
            result["error"] = str(e)[:100]
            result["status"] = "partial"
    
    # Update Neo4j
    if graph_repo:
        try:
            query = """
            MATCH (e:Episode {id: $episode_id})
            SET e.status = 'READY',
                e.summary = $summary,
                e.model = $model,
                e.vector_status = $vector_status,
                e.updated_at = datetime()
            """
            await graph_repo.query(query, {
                "episode_id": episode_id,
                "summary": summary,
                "model": model,
                "vector_status": result["vector_status"]
            })
        except Exception as e:
            logger.error(f"[EpisodeService] Neo4j update failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)[:100]
    
    return result


class EpisodeService:
    """Episode Pipeline Service singleton wrapper."""
    
    def __init__(self, graph_repo = None, vector_repo = None, embedder = None, llm_provider = None):
        self.graph_repo = graph_repo
        self.vector_repo = vector_repo
        self.embedder = embedder
        self.llm_provider = llm_provider
    
    async def summarize_turns(self, turns: List[Dict]) -> str:
        return await summarize_turns(turns, self.llm_provider)
    
    async def finalize_episode(
        self,
        episode_id: str,
        user_id: str,
        session_id: str,
        summary: str,
        model: str = "unknown"
    ) -> Dict[str, Any]:
        return await finalize_episode(
            episode_id, user_id, session_id, summary, model,
            self.graph_repo, self.vector_repo, self.embedder
        )


episode_service = EpisodeService()
