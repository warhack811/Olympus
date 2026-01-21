from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
import logging
import time

from app.repositories.graph_db import graph_repo
from app.core.telemetry.service import telemetry, EventType
from app.core.predicate_catalog import get_catalog, canonicalize_predicate

logger = logging.getLogger("app.service.memory.mwg")

class Decision(str, Enum):
    """MWG Decision outcomes."""
    DISCARD = "DISCARD"          # Do not write
    SESSION = "SESSION"          # Temporary session memory (RAM/Redis)
    EPHEMERAL = "EPHEMERAL"       # TTL-based temporary memory
    LONG_TERM = "LONG_TERM"       # Permanent memory (Neo4j)
    PROSPECTIVE = "PROSPECTIVE"   # Future tasks/reminders

@dataclass
class MemoryPolicy:
    """
    User-based memory policy.
    """
    mode: str = "STANDARD"  # OFF | STANDARD | FULL
    write_enabled: bool = True
    prospective_enabled: bool = True
    
    thresholds: Dict[str, float] = field(default_factory=lambda: {
        "utility": 0.6,
        "stability": 0.6,
        "confidence": 0.6,
        "recurrence": 1
    })
    
    ttl_defaults: Dict[str, int] = field(default_factory=lambda: {
        "EPHEMERAL_SECONDS": 86400,  # 24 hours
        "SESSION_SECONDS": 7200       # 2 hours
    })

@dataclass
class MWGResult:
    """MWG Decision result."""
    decision: Decision
    ttl_seconds: Optional[int] = None
    reason: str = ""
    scores: Dict[str, float] = field(default_factory=dict)

class MemoryWriteGate:
    """
    Decision engine for memory persistence.
    Determines if an extracted triplet should be stored in Long Term, Ephemeral, or discarded.
    """
    
    def __init__(self):
        self._catalog = get_catalog()
        # Fallback sets when catalog is unavailable
        self.identity_predicates = {"ISIM", "YASI", "MESLEGI", "LAKABI", "GELDIGI_YER"}
        self.preference_predicates = {"SEVER", "SEVMEZ", "SEVMIYOR", "ILGILENIR", "NEFRET_EDER"}
        self.ephemeral_predicates = {"NEREDE", "HISSEDIYOR", "YAPIYOR"}

    def _get_utility_score(self, predicate: str) -> float:
        if self._catalog:
            entry = self._catalog.get_entry(predicate)
            if entry:
                category = str(entry.get("category", "general")).lower()
                durability = str(entry.get("durability", "LONG_TERM")).upper()
                if durability in {"EPHEMERAL", "SESSION"}:
                    return 0.3
                category_weights = {
                    "identity": 0.9,
                    "preference": 0.8,
                    "relationship": 0.8,
                    "experience": 0.6,
                    "goal": 0.6,
                    "location": 0.7,
                }
                return category_weights.get(category, 0.5)
        if predicate in self.identity_predicates:
            return 0.9
        if predicate in self.preference_predicates:
            return 0.8
        if predicate in self.ephemeral_predicates:
            return 0.3
        return 0.5

    def _get_stability_score(self, predicate: str) -> float:
        if self._catalog:
            entry = self._catalog.get_entry(predicate)
            if entry:
                category = str(entry.get("category", "general")).lower()
                durability = str(entry.get("durability", "LONG_TERM")).upper()
                if durability in {"EPHEMERAL", "SESSION"}:
                    return 0.2
                category_weights = {
                    "identity": 0.9,
                    "preference": 0.6,
                    "relationship": 0.7,
                    "experience": 0.5,
                    "goal": 0.5,
                    "location": 0.7,
                }
                return category_weights.get(category, 0.6)
        if predicate in self.identity_predicates:
            return 0.9
        if predicate in self.ephemeral_predicates:
            return 0.2
        return 0.6

    async def decide(self, user_id: str, triplet: Dict[str, Any], policy: MemoryPolicy) -> MWGResult:
        """
        Decision logic for memory writing.
        """
        if not policy.write_enabled:
            return MWGResult(Decision.DISCARD, reason="Memory writing is disabled in policy.")

        subject = triplet.get("subject", "")
        predicate = canonicalize_predicate(triplet.get("predicate", ""), allow_unknown=True) or ""
        obj = triplet.get("object", "")
        confidence = triplet.get("confidence", 0.7)

        importance = triplet.get("importance", 0.5)
        sentiment = triplet.get("sentiment", "neutral")
        
        # Boost importance for negative sentiment (experience friction)
        if sentiment == "negative" and importance > 0.3:
            importance += 0.1

        # 1. Scoring
        utility = self._get_utility_score(predicate)
        stability = self._get_stability_score(predicate)
        
        # 2. Recurrence check (Peşkeş / Boost)
        recurrence = 0
        try:
            query = """
            MATCH (s:Entity {name: $s})-[r:FACT {user_id: $uid, predicate: $p}]->(o:Entity {name: $o})
            RETURN count(r) > 0 as exists
            """
            res = await graph_repo.query(query, {"s": subject, "p": predicate, "o": obj, "uid": user_id})
            if res and res[0].get("exists"):
                recurrence = 1
        except Exception as e:
            logger.warning(f"Recurrence check failed: {e}")

        scores = {
            "utility": utility,
            "stability": stability,
            "confidence": confidence,
            "recurrence": recurrence,
            "importance": importance,
            "sentiment": sentiment
        }

        # 3. Final Decision
        th = policy.thresholds
        
        # A. Critical Importance (LONG_TERM)
        if importance >= 0.8 and confidence >= 0.5:
            return MWGResult(Decision.LONG_TERM, reason=f"Critical information (I={importance:.2f})", scores=scores)

        # B. Standard Threshold (LONG_TERM)
        if (utility >= th["utility"] and stability >= th["stability"] and confidence >= th["confidence"] and importance >= 0.4):
            return MWGResult(Decision.LONG_TERM, reason="High integrity scores detected.", scores=scores)
        
        # C. Recurrence Boost
        if recurrence >= 1 and utility >= th["utility"]:
            return MWGResult(Decision.LONG_TERM, reason="Fact reinforced by recurrence.", scores=scores)

        # D. Ephemeral Fallback
        if importance >= 0.1 or utility >= 0.3:
            return MWGResult(
                Decision.EPHEMERAL, 
                ttl_seconds=policy.ttl_defaults["EPHEMERAL_SECONDS"],
                reason=f"Stored as ephemeral (I={importance:.2f})",
                scores=scores
            )

        return MWGResult(Decision.DISCARD, reason="Low relevance/importance.", scores=scores)

mwg = MemoryWriteGate()
