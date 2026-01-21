"""
Mami AI - Lifecycle Engine (Atlas Sovereign Edition)
----------------------------------------------------
EXCLUSIVE/ADDITIVE predicate lifecycle yönetimi.

Temporal conflict resolution sağlar:
- EXCLUSIVE: Aynı (subject, predicate) için sadece bir ACTIVE object
- ADDITIVE: Aynı (subject, predicate) için N ACTIVE object

Örnek:
- YAŞAR_YER İstanbul → Ankara: Eski ilişki SUPERSEDED olur
- SEVER Pizza + SEVER Sushi: İkisi de ACTIVE kalır
"""

import logging
from typing import List, Dict, Tuple

from app.core.predicate_catalog import get_catalog, canonicalize_predicate

logger = logging.getLogger(__name__)


# Predicate türleri
EXCLUSIVE_PREDICATES = {
    "ISIM", "YASI", "MESLEGI", "YASAR_YER", "GELDIGI_YER",
    "LAKABI", "ESI", "DOGUM_TARIHI"
}

ADDITIVE_PREDICATES = {
    "SEVER", "SEVMIYOR", "ISTIYOR", "OGRENMEK_ISTIYOR",
    "ARKADASI", "AILE_UYESI", "COCUGU", "HOBISI"
}


def get_predicate_type(predicate: str) -> str:
    """Predicate türünü döner: EXCLUSIVE veya ADDITIVE."""
    canonical_predicate = canonicalize_predicate(predicate, allow_unknown=True) or predicate
    catalog = get_catalog()
    if catalog:
        entry = catalog.get_entry(canonical_predicate)
        if entry:
            pred_type = str(entry.get("type", "ADDITIVE")).upper()
            if pred_type in {"EXCLUSIVE", "ADDITIVE"}:
                return pred_type
    if canonical_predicate.upper() in EXCLUSIVE_PREDICATES:
        return "EXCLUSIVE"
    elif canonical_predicate.upper() in ADDITIVE_PREDICATES:
        return "ADDITIVE"
    return "ADDITIVE"  # Default


async def resolve_conflicts(
    triplets: List[Dict],
    user_id: str,
    source_turn_id: str,
    graph_repo = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    EXCLUSIVE/ADDITIVE lifecycle kurallarını uygula.
    
    Args:
        triplets: LONG_TERM triplet'ler (MWG'den geçmiş)
        user_id: Kullanıcı ID
        source_turn_id: Mevcut turn ID
        graph_repo: Graph repository (opsiyonel)
    
    Returns:
        (new_triplets, supersede_operations)
    """
    new_triplets = []
    supersede_operations = []
    
    for triplet in triplets:
        predicate = triplet.get("predicate", "")
        subject = triplet.get("subject", "")
        obj = triplet.get("object", "")
        confidence = triplet.get("confidence", 0.8)
        
        pred_type = get_predicate_type(predicate)
        
        if pred_type == "EXCLUSIVE":
            # Check for existing ACTIVE relationship
            existing = None
            if graph_repo:
                existing = await _find_active_relationship(
                    graph_repo, user_id, subject, predicate
                )
            
            if existing:
                existing_object = existing.get("object")
                existing_confidence = existing.get("confidence", 1.0)
                
                if existing_object == obj:
                    # Same value - update
                    logger.info(f"Lifecycle EXCLUSIVE: Same value '{subject}' {predicate} '{obj}'")
                    new_triplets.append(triplet)
                else:
                    # Conflict detection
                    CONFLICT_THRESHOLD = 0.7
                    if existing_confidence >= CONFLICT_THRESHOLD and confidence >= CONFLICT_THRESHOLD:
                        logger.warning(
                            f"Lifecycle CONFLICT: '{subject}' {predicate}: "
                            f"'{existing_object}' vs '{obj}'"
                        )
                        supersede_operations.append({
                            "type": "CONFLICT",
                            "user_id": user_id,
                            "subject": subject,
                            "predicate": predicate,
                            "old_object": existing_object,
                            "new_object": obj,
                            "new_turn_id": source_turn_id
                        })
                        triplet["status"] = "CONFLICTED"
                        new_triplets.append(triplet)
                    else:
                        # Supersede low confidence
                        logger.info(
                            f"Lifecycle EXCLUSIVE: '{existing_object}' → '{obj}' (superseding)"
                        )
                        supersede_operations.append({
                            "type": "SUPERSEDE",
                            "user_id": user_id,
                            "subject": subject,
                            "predicate": predicate,
                            "old_object": existing_object,
                            "new_turn_id": source_turn_id
                        })
                        new_triplets.append(triplet)
            else:
                # No existing - create new
                logger.info(f"Lifecycle EXCLUSIVE: New '{subject}' {predicate} '{obj}'")
                new_triplets.append(triplet)
        
        elif pred_type == "ADDITIVE":
            # Check for exact match
            exact_exists = False
            if graph_repo:
                exact_exists = await graph_repo.fact_exists(user_id, subject, predicate, obj)
            
            if exact_exists:
                logger.info(f"Lifecycle ADDITIVE: Recurrence '{subject}' {predicate} '{obj}'")
            else:
                logger.info(f"Lifecycle ADDITIVE: Accumulate '{subject}' {predicate} '{obj}'")
            
            new_triplets.append(triplet)
        
        else:
            # Unknown type - default ADDITIVE
            new_triplets.append(triplet)
    
    return new_triplets, supersede_operations


async def _find_active_relationship(
    graph_repo,
    user_id: str,
    subject: str,
    predicate: str
) -> Dict:
    """Belirtilen subject+predicate için ACTIVE ilişkiyi bul."""
    try:
        query = """
        MATCH (s:Entity {name: $subject})-[r:FACT {predicate: $predicate, user_id: $uid}]->(o:Entity)
        WHERE r.status IS NULL OR r.status = 'ACTIVE'
        RETURN o.name as object, r.confidence as confidence
        LIMIT 1
        """
        result = await graph_repo.query(query, {
            "uid": user_id,
            "subject": subject,
            "predicate": predicate
        })
        return result[0] if result else None
    except Exception as e:
        logger.warning(f"_find_active_relationship error: {e}")
        return None
