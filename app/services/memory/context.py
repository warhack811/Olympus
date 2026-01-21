import logging
import asyncio
from typing import List, Dict, Any, Optional

from app.repositories.graph_db import graph_repo
from app.repositories.vector_db import vector_repo
from app.core.telemetry.service import telemetry, EventType
from app.core.predicate_catalog import get_catalog

logger = logging.getLogger("app.service.memory.context")

class ContextBuilder:
    """
    Builds a rich context for the AI by combining Graph (structural) and Vector (semantic) memory.
    """
    
    def __init__(self):
        catalog = get_catalog()
        if catalog:
            # We fetch both identity and hard_facts (Preferences, Allergies, etc.)
            self.identity_preds = catalog.get_predicates_by_group("identity", include_aliases=True)
            self.identity_preds.extend(catalog.get_predicates_by_group("hard_facts", include_aliases=True))
            # Deduplicate
            self.identity_preds = list(set(self.identity_preds))
        else:
            # Identity predicates that are always prioritized in context
            self.identity_preds = ["ISIM", "YASI", "MESLEGI", "YASAR_YER", "LAKABI", "ALERJISI", "SAGLIK_DURUMU"]

    async def get_identity_facts(self, user_id: str) -> List[Dict[str, str]]:
        """Retrieves core identity facts from the knowledge graph."""
        query = """
        MATCH (s:Entity)-[r:FACT {user_id: $uid}]->(o:Entity)
        WHERE r.predicate IN $preds AND (r.status IS NULL OR r.status = 'ACTIVE')
        RETURN r.predicate as predicate, o.name as value
        """
        results = await graph_repo.query(query, {"uid": user_id, "preds": self.identity_preds})
        return [{"predicate": r["predicate"], "value": r["value"]} for r in results]

    async def get_semantic_facts(self, message_vector: List[float], limit: int = 5) -> List[str]:
        """Retrieves semantically similar memories from Qdrant."""
        try:
            hits = await vector_repo.search(vector=message_vector, limit=limit, score_threshold=0.6)
            return [hit["payload"].get("text", "") for hit in hits if "text" in hit["payload"]]
        except Exception as e:
            logger.error(f"Semantic search failed during context building: {e}")
            return []

    async def build_context(self, user_id: str, message: str, message_vector: Optional[List[float]] = None) -> str:
        """
        Builds the final formatted context string.
        """
        # RC-7: Noise Guard - Avoid noise for simple/general questions
        noise_keywords = {"saat", "gün", "hava", "kaç", "nedir", "kimdir", "başla", "dur"}
        words = set(message.lower().split())
        if len(words) < 4 and words.intersection(noise_keywords):
            return ""

        # Parallel retrieval
        identity_task = self.get_identity_facts(user_id)
        semantic_task = self.get_semantic_facts(message_vector) if message_vector else asyncio.sleep(0, result=[])
        
        identity_facts, semantic_memories = await asyncio.gather(identity_task, semantic_task)

        # Formatting
        context_parts = []
        
        if identity_facts:
            context_parts.append("### KULLANICI PROFİLİ")
            for f in identity_facts:
                context_parts.append(f"- {f['predicate']}: {f['value']}")
        
        if semantic_memories:
            context_parts.append("\n### İLGİLİ HAFIZA")
            for i, mem in enumerate(semantic_memories, 1):
                context_parts.append(f"{i}. {mem}")

        final_context = "\n".join(context_parts)
        
        telemetry.emit(
            EventType.MEMORY_OP, 
            {
                "op": "build_context",
                "identity_count": len(identity_facts),
                "semantic_count": len(semantic_memories),
                "context_length": len(final_context)
            },
            component="context_builder"
        )
        
        return final_context

context_builder = ContextBuilder()
