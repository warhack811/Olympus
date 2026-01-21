
"""
Mami AI - Memory Gateway (Unified Retrieval Layer)
-------------------------------------------------
Orchestrates high-level contextual memory retrieval from all tiers.
Handles deduplication and ranking.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.services.memory.scorer import memory_scorer
from app.services.memory.manager import memory_manager
from app.memory.conversation_archive import ConversationArchive
from app.services.brain.memory.embeddings import embedder
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger("app.service.memory.gateway")

class MemoryGateway:
    """
    The 'Single Point of Truth' for memory context.
    Replaces fragmented retrieval logic in BrainEngine.
    """
    
    async def get_unified_context(
        self,
        user_id: str,
        session_id: str,
        query: str,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        Retrieves and synthesizes context from all memory tiers.
        """
        from app.core.constants import HISTORY_LIMITS
        if limit is None:
            limit = HISTORY_LIMITS.get("memory_gateway", 8)
        
        logger.info(f"[MemoryGateway] Fetching unified context for session: {session_id} (limit={limit})")
        
        # 1. Generate query vector for semantic retrieval
        query_vector = await embedder.embed(query)
        
        # 2. Parallel Retrieval from all tiers
        tasks = [
            # Tier 1: Core Personality/Identity (Graph + Vector)
            memory_manager.get_user_context(user_id, query, message_vector=query_vector),
            
            # Tier 2: Episodic Archive (Summaries + Vectors)
            ConversationArchive.search_past_conversations(user_id, query, limit=limit),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        graph_raw = results[0] if not isinstance(results[0], Exception) else ""
        archive_results = results[1] if not isinstance(results[1], Exception) else []
        
        # 2. Scorer Application (Reranking Archive)
        if isinstance(archive_results, list) and archive_results:
            # Archive results are already quite structured. 
            # We apply IDR logic if importance/dates are present.
            # ArchiveSearchResult typically has relevance_score, importance, created_at.
            
            # Convert ArchiveSearchResult to dict for scorer if needed
            to_score = []
            for res in archive_results:
                to_score.append({
                    "text": res.summary or "",
                    "score": res.relevance_score,
                    "score_type": "hybrid_distance", # SearchArchive uses similarity-like scores
                    "importance": getattr(res, "importance", 1),
                    "created_at": res.created_at,
                    "filename": res.title
                })
            
            scored_archive = memory_scorer.rerank_results(query, to_score)
        else:
            scored_archive = []

        # 3. Deduplication (Ensures L2 summaries don't repeat L3 graph facts)
        # Simple heuristic: If a summary is 90% similar to graph context, skip.
        final_memories = []
        for res in scored_archive:
            if res["text"] and len(res["text"]) > 20: 
                # Check if already in graph_raw
                if res["text"][:50] not in graph_raw:
                    final_memories.append(res)

        return {
            "graph_context": graph_raw,
            "episodic_memories": final_memories[:limit],
            "total_scored": len(scored_archive)
        }

    def format_context_for_llm(self, context_data: Dict[str, Any]) -> str:
        """Formats the unified data into a clean prompt string."""
        parts = []
        
        gc = context_data.get("graph_context", "")
        if gc:
            parts.append(gc) # Already has headers like ### KULLANICI PROFİLİ
            
        em = context_data.get("episodic_memories", [])
        if em:
            parts.append("\n### ÖNCEKİ KONUŞMALARDAN NOTLAR")
            for i, m in enumerate(em, 1):
                importance = m.get('importance', 1)
                text = m.get('text', '')[:300]  # Truncate to 300 chars
                parts.append(f"{i}. [Önem: {importance}/10] {text}")
                
        return "\n".join(parts)

memory_gateway = MemoryGateway()
