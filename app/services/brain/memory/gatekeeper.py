"""
Mami AI - Memory Gatekeeper (MWG - Atlas Sovereign Edition)
-----------------------------------------------------------
Merkezi hafıza yazma kararı motoru.

Her triplet için "nereye yazılacak?" kararını verir:
- DISCARD: Hiçbir yere yazılmaz
- SESSION: Oturum hafızası
- EPHEMERAL: TTL ile geçici
- LONG_TERM: Kalıcı hafıza (Neo4j)
- PROSPECTIVE: Gelecek task/reminder
"""

import logging
from typing import Dict, Optional
from enum import Enum

from app.services.brain.memory.schemas import MemoryDecision, MWGResult, Triplet
from app.config import get_settings
from app.core.predicate_catalog import get_catalog, canonicalize_predicate

logger = logging.getLogger(__name__)


# Prospective intent kelimeleri
PROSPECTIVE_KEYWORDS = [
    "hatırlat", "hatırla", "unutma", "remind", "reminder",
    "yarın", "haftaya", "gelecek", "sonra", "bugün",
    "saat", "dakika", "tarih"
]


def is_prospective_intent(text: str) -> bool:
    """Mesajda prospective/reminder intent var mı kontrol et."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in PROSPECTIVE_KEYWORDS)


def compute_utility_score(predicate_key: str, category: str) -> float:
    """Utility skoru: Bilginin faydalılığı (0.0-1.0)."""
    catalog = get_catalog()
    if catalog:
        entry = catalog.get_entry(predicate_key)
        if entry:
            entry_category = str(entry.get("category", category or "general")).lower()
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
            return category_weights.get(entry_category, 0.5)
    # Identity predicates
    identity = ["ISIM", "YASI", "MESLEGI", "GELDIGI_YER", "LAKABI"]
    if predicate_key in identity:
        return 0.9
    
    # Preferences
    preferences = ["SEVER", "SEVMIYOR", "ISTIYOR", "OGRENMEK_ISTIYOR"]
    if predicate_key in preferences:
        return 0.8
    
    # Relationships
    relationships = ["ESI", "ARKADASI", "AILE_UYESI", "COCUGU"]
    if predicate_key in relationships:
        return 0.8
    
    # Ephemeral state
    state = ["NEREDE", "HISSEDIYOR"]
    if predicate_key in state:
        return 0.3
    
    if category == "personal":
        return 0.7
    
    return 0.5


def compute_stability_score(durability: str) -> float:
    """Stability skoru: Bilginin istikrarı (0.0-1.0)."""
    durability_map = {
        "STATIC": 1.0,
        "LONG_TERM": 0.8,
        "SESSION": 0.4,
        "EPHEMERAL": 0.2
    }
    return durability_map.get(durability, 0.6)


async def decide(
    triplet: Dict,
    user_id: str,
    raw_text: str = "",
    thresholds: Dict[str, float] = None
) -> MWGResult:
    """
    Bir triplet için MWG kararı ver (rule-based).
    
    Args:
        triplet: subject-predicate-object dict
        user_id: Kullanıcı ID
        raw_text: Orijinal mesaj (intent detection için)
        thresholds: Özel eşik değerleri
    
    Returns:
        MWGResult (decision, ttl, reason, scores)
    """
    settings = get_settings()
    
    # Default thresholds
    if thresholds is None:
        thresholds = {
            "utility": 0.5,
            "stability": 0.4,
            "confidence": 0.5
        }
    
    # Memory mode kontrolü
    memory_mode = settings.ATLAS_MEMORY_MODE
    if memory_mode == "OFF":
        if is_prospective_intent(raw_text):
            return MWGResult(
                decision=MemoryDecision.PROSPECTIVE,
                reason="memory_mode=OFF ama prospective intent var"
            )
        return MWGResult(decision=MemoryDecision.DISCARD, reason="memory_mode=OFF")
    
    predicate = triplet.get("predicate", "")
    category = triplet.get("category", "general")
    confidence = triplet.get("confidence", 0.7)
    
    # Durability mapping (basitleştirilmiş)
    canonical_predicate = canonicalize_predicate(predicate, allow_unknown=True) or predicate
    category = category or "general"
    durability = "LONG_TERM"
    catalog = get_catalog()
    if catalog:
        entry = catalog.get_entry(canonical_predicate)
        if entry:
            category = str(entry.get("category", category)).lower()
            durability = str(entry.get("durability", "LONG_TERM")).upper()
            if durability in {"EPHEMERAL", "SESSION"}:
                return MWGResult(
                    decision=MemoryDecision.EPHEMERAL,
                    ttl_seconds=86400,
                    reason=f"Ephemeral predicate: {canonical_predicate}"
                )
    ephemeral_predicates = ["HISSEDIYOR", "NEREDE"]
    session_predicates = []
    
    if canonical_predicate in ephemeral_predicates:
        return MWGResult(
            decision=MemoryDecision.EPHEMERAL,
            ttl_seconds=86400,
            reason=f"Ephemeral predicate: {canonical_predicate}"
        )
    
    if predicate in session_predicates:
        return MWGResult(
            decision=MemoryDecision.SESSION,
            ttl_seconds=7200,
            reason=f"Session predicate: {predicate}"
        )
    
    importance = triplet.get("importance", 0.5)
    sentiment = triplet.get("sentiment", "neutral")
    
    # Duygu bazlı ayar (Nagatif duygular hatırlanmalı)
    if sentiment == "negative" and importance > 0.3:
        importance += 0.1
    
    # Scoring
    utility = compute_utility_score(canonical_predicate, category)
    stability = compute_stability_score(durability)
    
    scores = {
        "utility": utility,
        "stability": stability,
        "confidence": confidence,
        "importance": importance,
        "sentiment_score": 1.0 if sentiment != "neutral" else 0.5
    }
    
    # 1. KRİTİK BİLGİ (LONG_TERM)
    if importance >= 0.8 and confidence >= 0.5:
        return MWGResult(
            decision=MemoryDecision.LONG_TERM,
            reason=f"Kritik Bilgi: I={importance:.2f}, C={confidence:.2f}",
            scores=scores
        )
    
    # 2. STANDART EŞİK KONTROLÜ (LONG_TERM)
    if (utility >= thresholds["utility"] and 
        stability >= thresholds["stability"] and 
        confidence >= thresholds["confidence"] and
        importance >= 0.4):
        return MWGResult(
            decision=MemoryDecision.LONG_TERM,
            reason=f"Eşik üstü: U={utility:.2f}, I={importance:.2f}",
            scores=scores
        )
    
    # 3. ÖNEMSİZ DETAY (DISCARD)
    if importance <= 0.2 and sentiment == "neutral":
        return MWGResult(
            decision=MemoryDecision.DISCARD,
            reason=f"Önemsiz detay: I={importance:.2f}",
            scores=scores
        )
    
    # 4. VARSAYILAN (EPHEMERAL)
    return MWGResult(
        decision=MemoryDecision.EPHEMERAL,
        ttl_seconds=86400,
        reason=f"Geçici Hafıza: I={importance:.2f}",
        scores=scores
    )


class MemoryWriteGate:
    """Memory Write Gate singleton wrapper."""
    
    @staticmethod
    async def decide(triplet: Dict, user_id: str, raw_text: str = "") -> MWGResult:
        return await decide(triplet, user_id, raw_text)


memory_write_gate = MemoryWriteGate()
