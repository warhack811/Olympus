
"""
Mami AI - Memory Scorer (Stanford Generative Agents Pattern)
-----------------------------------------------------------
Implements the IDR (Importance, Decay, Relatedness) scoring algorithm.
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

logger = logging.getLogger("app.service.memory.scorer")

class MemoryScorer:
    """
    Computes a unified score for memory objects.
    Reference: Stanford 'Generative Agents' (2.1 Memory Stream)
    """
    
    # Weight Constants (Industry Best Practice)
    W_RELATEDNESS = 1.0  # Semantic similarity
    W_IMPORTANCE = 1.0   # LLM-assigned importance
    W_RECENCY = 1.0      # Time decay
    
    # Decay hyperparameter (0.99 means 1% decay per hour)
    DECAY_FACTOR = 0.995 

    @classmethod
    def score_memory(
        cls,
        similarity: float, # 0 to 1
        importance: int,   # 1 to 10
        created_at: datetime
    ) -> float:
        """
        Calculates the final score for a memory item.
        """
        # 1. Relatedness (Already provided by vector/lexical search)
        rel_score = similarity
        
        # 2. Importance (Normalized to 0.0 - 1.0)
        imp_score = importance / 10.0
        
        # 3. Recency (Decay function)
        # Hours since created
        now = datetime.now(timezone.utc)
        
        # Ensure naive vs aware mismatch handle
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
            
        hours_passed = max(0, (now - created_at).total_seconds() / 3600.0)
        rec_score = math.pow(cls.DECAY_FACTOR, hours_passed)
        
        # Final weighted combination
        final_score = (
            (rel_score * cls.W_RELATEDNESS) +
            (imp_score * cls.W_IMPORTANCE) +
            (rec_score * cls.W_RECENCY)
        ) / (cls.W_RELATEDNESS + cls.W_IMPORTANCE + cls.W_RECENCY)
        
        return final_score

    @classmethod
    def rerank_results(cls, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reranks raw search results using IDR scoring.
        Expects results list with 'score' (similarity), 'importance', and 'created_at'.
        """
        for res in results:
            # If similarity is in 'score', it's usually distance (smaller is better) for Qdrant/Chroma
            # Convert distance to similarity if needed
            sim = res.get("score", 0.0)
            if res.get("score_type") in ["distance", "hybrid_distance"]:
                sim = 1.0 - sim
            
            imp = res.get("importance", 1)
            created = res.get("created_at")
            if not isinstance(created, datetime):
                try:
                    # Handle string dates if necessary
                    created = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                except:
                    created = datetime.now(timezone.utc)
            
            res["idr_score"] = cls.score_memory(sim, imp, created)
        
        # Sort by idr_score descending
        results.sort(key=lambda x: x["idr_score"], reverse=True)
        return results

memory_scorer = MemoryScorer()
