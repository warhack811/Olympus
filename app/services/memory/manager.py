import logging
import uuid
from typing import List, Dict, Any, Optional

from app.repositories.graph_db import graph_repo
from app.repositories.vector_db import vector_repo
from app.services.memory.mwg import mwg, MemoryPolicy, Decision
from app.services.memory.context import context_builder
from app.core.predicate_catalog import canonicalize_predicate
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger("app.service.memory.manager")

class MemoryManager:
    """
    Main entry point for Memory Operations in Atlas & Mami AI.
    Orchestrates MWG, Context Builder, and Repositories.
    """
    
    async def get_user_context(self, user_id: str, message: str, message_vector: Optional[List[float]] = None) -> str:
        """
        Retrieves the unified memory context for a user interaction.
        """
        return await context_builder.build_context(user_id, message, message_vector)

    async def save_fact(self, user_id: str, triplet: Dict[str, Any], policy: Optional[MemoryPolicy] = None):
        """
        Evaluates and saves a fact to the appropriate memory layer.
        
        triplet format: {"subject": "X", "predicate": "Y", "object": "Z", "confidence": 0.9}
        """
        if policy is None:
            policy = MemoryPolicy() # Default policy

        # 1. MWG Decision
        mwg_result = await mwg.decide(user_id, triplet, policy)
        
        if mwg_result.decision == Decision.DISCARD:
            logger.info(f"Fact discarded by MWG: {triplet.get('predicate')} - {mwg_result.reason}")
            return False

        # 2. Extract Data
        subject = triplet.get("subject", "USER").upper()
        predicate = canonicalize_predicate(triplet.get("predicate", ""), allow_unknown=True) or ""
        obj = triplet.get("object", "")

        # 3. Save to Neo4j (Long Term)
        if mwg_result.decision == Decision.LONG_TERM:
            query = """
            MERGE (s:Entity {name: $s})
            MERGE (o:Entity {name: $o})
            MERGE (s)-[r:FACT {predicate: $p, user_id: $uid}]->(o)
            SET r.updated_at = timestamp(),
                r.status = 'ACTIVE',
                r.confidence = $conf
            RETURN r
            """
            try:
                await graph_repo.query(query, {
                    "s": subject,
                    "p": predicate,
                    "o": obj,
                    "uid": user_id,
                    "conf": triplet.get("confidence", 0.7)
                })
            except Exception as e:
                logger.error(f"Failed to save fact to Neo4j: {e}")
                return False

        # 4. Save to Qdrant (Semantic Indexing)
        # Note: We save a text representation of the fact for search
        fact_text = f"{subject} {predicate} {obj}"
        point_id = str(uuid.uuid4())
        
        # Note: Embedding generation should happen before vector_repo.upsert
        # For now, we assume search might use these via raw text or later hydration
        # In actual Phase 3, an 'extractor' will provide vectors.
        
        telemetry.emit(
            EventType.MEMORY_OP, 
            {
                "op": "save_fact",
                "decision": mwg_result.decision.value,
                "predicate": predicate,
                "user_id": user_id
            },
            component="memory_manager"
        )
        
        return True

    async def forget_fact(self, user_id: str, predicate: str, subject: str = "USER"):
        """
        Deletes or archives a fact from the knowledge graph.
        """
        query = """
        MATCH (s:Entity {name: $s})-[r:FACT {user_id: $uid, predicate: $p}]->(o:Entity)
        DELETE r
        """
        try:
            await graph_repo.query(query, {"s": subject, "p": predicate, "uid": user_id})
            
            telemetry.emit(
                EventType.MEMORY_OP, 
                {"op": "forget_fact", "predicate": predicate, "user_id": user_id},
                component="memory_manager"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete fact: {e}")
            return False

# Global Singleton Instance
memory_manager = MemoryManager()
