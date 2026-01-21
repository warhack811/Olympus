"""
Mami AI - Memory Context Builder (Atlas Sovereign Edition)
----------------------------------------------------------
Hibrit retrieval ve bağlam formatlama.

Sorumluluklar:
1. Graph Query: Neo4j'den identity ve fact bilgileri
2. Vector Search: Qdrant'dan semantik benzerlik
3. Format: Atlas "Kullanıcı Profili / Sert Gerçekler / Yumuşak Sinyaller" formatı
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.services.brain.memory.schemas import MemoryContext, Triplet
from app.services.brain.memory.engines.identity import get_user_anchor
from app.core.predicate_catalog import get_catalog

logger = logging.getLogger(__name__)


async def build_context(
    user_id: str,
    query: str,
    graph_repo = None,
    vector_repo = None,
    limit: int = 10
) -> str:
    """
    Kullanıcı bağlamını oluşturur.
    
    Args:
        user_id: Kullanıcı ID
        query: Kullanıcı sorgusu (vector search için)
        graph_repo: Graph repository
        vector_repo: Vector repository
        limit: Maksimum sonuç sayısı
    
    Returns:
        Formatlanmış bağlam stringi
    """
    context = MemoryContext(user_id=user_id)
    user_anchor = get_user_anchor(user_id)
    
    # 1. Identity facts from graph
    if graph_repo:
        try:
            identity_facts = await _fetch_identity_facts(graph_repo, user_id, user_anchor)
            context.identity_facts = identity_facts
        except Exception as e:
            logger.warning(f"Identity fetch error: {e}")
    
    # 2. Hard facts from graph
    if graph_repo:
        try:
            hard_facts = await _fetch_hard_facts(graph_repo, user_id, user_anchor, limit)
            context.hard_facts = hard_facts
        except Exception as e:
            logger.warning(f"Hard facts fetch error: {e}")
    
    # 3. Vector search for semantic context
    if vector_repo:
        try:
            vector_results = await vector_repo.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            context.vector_results = vector_results
        except Exception as e:
            logger.warning(f"Vector search error: {e}")
    
    return context.to_formatted_string()


async def _fetch_identity_facts(
    graph_repo,
    user_id: str,
    user_anchor: str
) -> List[Triplet]:
    """Identity predicate'lerini çeker."""
    catalog = get_catalog()
    if catalog:
        identity_predicates = catalog.get_predicates_by_group("identity", include_aliases=True)
    else:
        identity_predicates = ["ISIM", "YASI", "MESLEGI", "YASAR_YER", "GELDIGI_YER", "LAKABI"]
    
    try:
        query = """
        MATCH (s:Entity {name: $anchor})-[r:FACT]->(o:Entity)
        WHERE r.user_id = $uid AND r.predicate IN $predicates
        AND (r.status IS NULL OR r.status = 'ACTIVE')
        RETURN r.predicate as predicate, o.name as object, r.confidence as confidence, r.updated_at as updated_at
        """
        
        results = await graph_repo.query(query, {
            "anchor": user_anchor,
            "uid": user_id,
            "predicates": identity_predicates
        })
        
        return [
            Triplet(
                subject=user_anchor,
                predicate=r["predicate"],
                object=r["object"],
                confidence=r.get("confidence", 1.0),
                updated_at=r.get("updated_at"),
                category="identity"
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Identity query error: {e}")
        return []


async def _fetch_hard_facts(
    graph_repo,
    user_id: str,
    user_anchor: str,
    limit: int
) -> List[Triplet]:
    """Sert gerçekleri (preferences, relationships) çeker."""
    catalog = get_catalog()
    if catalog:
        hard_predicates = catalog.get_predicates_by_group("hard_facts", include_aliases=True)
    else:
        hard_predicates = ["SEVER", "SEVMIYOR", "ESI", "ARKADASI", "COCUGU", "HOBISI"]
    
    try:
        query = """
        MATCH (s:Entity)-[r:FACT]->(o:Entity)
        WHERE r.user_id = $uid AND r.predicate IN $predicates
        AND (r.status IS NULL OR r.status = 'ACTIVE')
        AND r.confidence >= 0.7
        RETURN s.name as subject, r.predicate as predicate, o.name as object, r.confidence as confidence, r.updated_at as updated_at
        ORDER BY r.updated_at DESC
        LIMIT $limit
        """
        
        results = await graph_repo.query(query, {
            "uid": user_id,
            "predicates": hard_predicates,
            "limit": limit
        })
        
        return [
            Triplet(
                subject=r["subject"],
                predicate=r["predicate"],
                object=r["object"],
                confidence=r.get("confidence", 0.8),
                updated_at=r.get("updated_at"),
                category="hard_fact"
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Hard facts query error: {e}")
        return []


def format_context_for_llm(context: MemoryContext) -> str:
    """LLM için bağlamı formatlar (Memory Voice uyumlu)."""
    parts = []
    
    if context.identity_facts:
        parts.append("<system_memory>")
        parts.append("[KULLANICI PROFİLİ]")
        for f in context.identity_facts:
            parts.append(f"  • {f.predicate}: {f.object}")
        parts.append("</system_memory>")
    
    if context.hard_facts:
        parts.append("\n[HATIRLADIKLARIM]")
        for f in context.hard_facts:
            conf_note = "(Emin değilim)" if f.confidence < 0.7 else ""
            parts.append(f"  • {f.subject} {f.predicate} {f.object} {conf_note}")
    
    if context.vector_results:
        parts.append("\n[İLGİLİ BAĞLAM]")
        for v in context.vector_results[:5]:
            parts.append(f"  • {v.get('content', '')[:100]}...")
    
    return "\n".join(parts) if parts else "[Hafıza kaydı yok]"


# Singleton helper
class ContextBuilder:
    """Context Builder singleton."""
    
    @staticmethod
    async def build(user_id: str, query: str, graph_repo=None, vector_repo=None) -> str:
        return await build_context(user_id, query, graph_repo, vector_repo)


context_builder = ContextBuilder()
