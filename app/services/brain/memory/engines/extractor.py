"""
Mami AI - Extractor Engine (Atlas Sovereign Edition)
----------------------------------------------------
LLM kullanarak metinden Triplet (Özne-Yüklem-Nesne) çıkarır.

Sorumluluklar:
1. Bilgi Tespiti: Kalıcı gerçekleri ayıklama
2. Formata Dönüştürme: JSON formatına çevirme
3. Filtreleme: Gereksiz verileri eleme
"""

import json
import logging
from typing import List, Dict, Any

from app.providers.llm.groq import GroqProvider
from app.core.prompts import EXTRACTOR_SYSTEM_PROMPT
from app.core.predicate_catalog import get_catalog, canonicalize_predicate
from app.services.brain.memory.engines.identity import (
    is_first_person, is_second_person, is_other_pronoun, get_user_anchor
)

logger = logging.getLogger(__name__)


# Null/placeholder values to filter
PLACEHOLDER_VALUES = [
    "bilinmiyor", "bilgi yok", "verilmemiş", "verilmemis",
    "tanımsız", "tanimsiz", "belirsiz", "none", "null", "bilgim yok"
]

# Command keywords to filter
COMMAND_KEYWORDS = [
    "unut", "sil", "temizle", "hafıza", "reset", "sıfırla", "geçmişi", "bilgileri"
]


async def extract_triplets(
    text: str,
    user_id: str,
    source_turn_id: str = None
) -> List[Dict]:
    """
    Metinden triplet'leri çıkarır.
    
    Args:
        text: Analiz edilecek metin
        user_id: Kullanıcı ID
        source_turn_id: Turn ID (provenance)
    
    Returns:
        Temizlenmiş triplet listesi
    """
    if not text or not text.strip() or len(text.strip()) < 5:
        return []
    
    # POINT 5: Memory Write Thought (LLM-driven)
    try:
        from app.services.brain.thought_generator import thought_generator
        from app.services.brain.context_enricher import context_enricher
        
        user_context = await context_enricher.get_user_context(user_id, text, [])
        memory_thought = await thought_generator.generate_thought(
            task_type="memory_write",
            user_context=user_context,
            action_params={"text": text[:100]},
            allow_fallback=False  # Point 5
        )
        logger.info(f"[POINT 5]: {memory_thought}")
    except Exception as e:
        logger.warning(f"[POINT 5] failed: {e}")
    
    try:
        # LLM extraction
        provider = GroqProvider()
        raw_response = await provider.generate(
            prompt=f"Kullanıcı mesajı: {text}",
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            temperature=0.1
        )
        
        if not raw_response:
            return []
        
        parsed = json.loads(raw_response)
        
        # Normalize structure
        triplets = []
        if isinstance(parsed, list):
            triplets = parsed
        elif isinstance(parsed, dict):
            triplets = parsed.get("triplets", parsed.get("facts", []))
            if not triplets and "subject" in parsed:
                triplets = [parsed]
        
        if not triplets:
            logger.info("No triplets extracted from message.")
            return []
        
        # Sanitize
        cleaned = sanitize_triplets(triplets, user_id, text)
        logger.info(f"Extracted {len(cleaned)} triplets from message.")
        
        return cleaned
        
    except json.JSONDecodeError:
        logger.debug("No valid JSON from extractor.")
        return []
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return []


def sanitize_triplets(
    triplets: List[Dict],
    user_id: str,
    raw_text: str
) -> List[Dict]:
    """
    Triplet'leri temizler ve doğrular.
    
    Filters:
    1. Required fields check
    2. First-person mapping
    3. Pronoun filter
    4. Command filter
    5. Placeholder filter
    6. Confidence filter
    """
    cleaned = []
    
    for triplet in triplets:
        subject = str(triplet.get("subject") or "").strip()
        predicate = str(triplet.get("predicate") or "").strip()
        obj = str(triplet.get("object") or "").strip()
        confidence = triplet.get("confidence", 0.8)

        canonical_predicate = canonicalize_predicate(predicate, allow_unknown=True) or predicate
        catalog = get_catalog()
        if catalog and canonical_predicate:
            if not catalog.is_enabled(canonical_predicate):
                logger.debug(f"DROP_DISABLED_PREDICATE: {canonical_predicate}")
                continue
        
        # Required fields
        if not subject or not predicate or not obj:
            continue
        
        # Command filter
        obj_lower = obj.lower()
        if canonical_predicate in ["ISTIYOR", "PLANLIYOR"]:
            if any(kw in obj_lower for kw in COMMAND_KEYWORDS):
                logger.debug(f"DROP_COMMAND: {obj}")
                continue
        
        # Placeholder filter
        if any(ph in obj_lower for ph in PLACEHOLDER_VALUES):
            logger.debug(f"DROP_PLACEHOLDER: {obj}")
            continue
        
        # Confidence filter
        if confidence < 0.4:
            logger.debug(f"DROP_LOW_CONFIDENCE: {confidence}")
            continue
        
        # Pronoun handling
        if is_first_person(subject):
            subject = get_user_anchor(user_id)
            logger.debug(f"MAPPED_FIRST_PERSON: {triplet.get('subject')} → {subject}")
        elif is_second_person(subject):
            logger.debug(f"DROP_SECOND_PERSON: {subject}")
            continue
        elif is_other_pronoun(subject):
            logger.debug(f"DROP_OTHER_PRONOUN: {subject}")
            continue
        
        # Build cleaned triplet
        resolved_category = triplet.get("category", "personal")
        if catalog and canonical_predicate:
            entry = catalog.get_entry(canonical_predicate)
            if entry:
                entry_category = str(entry.get("category", resolved_category))
                if entry_category:
                    resolved_category = entry_category

        cleaned.append({
            "subject": subject,
            "predicate": canonical_predicate,
            "object": obj,
            "category": resolved_category,
            "confidence": confidence,
            "importance": triplet.get("importance", 0.5),
            "sentiment": triplet.get("sentiment", "neutral")
        })
    
    return cleaned
