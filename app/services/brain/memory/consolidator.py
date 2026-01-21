"""
Mami AI - Memory Consolidator (Atlas Sovereign Edition)
------------------------------------------------------
Epizodik anıları analiz eder ve kalıcı gerçeklere (triplet) dönüştürür.
Hafıza enflasyonunu önlemek için periyodik temizlik ve özetleme yapar.
"""

import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from app.repositories.graph_db import graph_repo
from app.services.brain.memory.engines.extractor import extract_triplets
from app.services.memory.manager import memory_manager

logger = logging.getLogger(__name__)

CONSOLIDATOR_PROMPT_TEMPLATE = """
Sen bir hafıza analiz uzmanısın. Kullanıcının aşağıdaki kısaltılmış anılarını (episodes) incele.
Bu anılardan çıkarılabilecek, daha önce kaydedilmemiş ÖNEMLİ ve KALICI gerçekleri (FACT) tespit et.

ANILAR:
{summaries}

Görevin:
1. Bu anıları sentezle.
2. Kalıcı değer taşıyan bilgileri Triplet formatında çıkar.
3. Önemli olmayan günlük sohbetleri ele.

Sadece yeni ve önemli gerçekleri çıkar.
"""

class ConsolidatorService:
    """Hafıza pekiştirme ve temizlik servisi."""

    def __init__(self):
        self.graph_repo = graph_repo
        self.memory_manager = memory_manager

    async def consolidate_user_memories(self, user_id: str, limit: int = 10):
        """
        Kullanıcının işlenmemiş anılarını pekiştirir.
        """
        logger.info(f"[Consolidator] Starting consolidation for user: {user_id}")
        
        # 1. İşlenmemiş (READY ama CONSOLIDATED değil) anıları getir
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_EPISODE]->(e:Episode)
        WHERE e.status = 'READY' AND (e.consolidated IS NULL OR e.consolidated = false)
        RETURN e.id as id, e.summary as summary, e.created_at as created_at
        ORDER BY e.created_at ASC
        LIMIT $limit
        """
        episodes = await self.graph_repo.query(query, {"user_id": user_id, "limit": limit})
        
        if not episodes:
            logger.info(f"[Consolidator] No episodes to consolidate for {user_id}")
            return 0

        # 2. Anıları birleştir ve LLM'e gönder
        summaries_text = "\n".join([f"- {ep['summary']}" for ep in episodes])
        combined_text = f"Kullanıcı ile ilgili son anılar:\n{summaries_text}"
        
        # 3. Triplet çıkarımı (Mevcut extractor'ı kullanıyoruz ama daha derin analiz için)
        # Not: extract_triplets zaten LLM çağrısı yapar.
        new_triplets = await extract_triplets(combined_text, user_id)
        
        if new_triplets:
            logger.info(f"[Consolidator] Extracted {len(new_triplets)} potential facts from consolidation.")
            # 4. Triplet'leri kaydet (MemoryManager üzerinden MWG süzgecinden geçer)
            for triplet in new_triplets:
                # Consolidation sırasında gelen bilgiler genellikle önemlidir, 
                # ancak yine de MWG'den geçmesi güvenlidir.
                await self.memory_manager.save_fact(user_id, triplet)
        
        # 5. Anıları 'CONSOLIDATED' olarak işaretle
        episode_ids = [ep["id"] for ep in episodes]
        mark_query = """
        MATCH (e:Episode)
        WHERE e.id IN $ids
        SET e.consolidated = true, e.consolidated_at = datetime()
        """
        await self.graph_repo.query(mark_query, {"ids": episode_ids})
        
        logger.info(f"[Consolidator] Successfully consolidated {len(episode_ids)} episodes for {user_id}")
        return len(episode_ids)

    async def optimize_graph(self, user_id: str):
        """
        GraphDB üzerinde periyodik temizlik yapar (SUPERSEDED düğümler vb.).
        """
        logger.info(f"[Consolidator] Optimizing graph for user: {user_id}")
        
        # Örnek: 1 aydan eski ve SUPERSEDED olan fact düğümlerini sil
        cleanup_query = """
        MATCH (u:User {id: $user_id})-[:FACT]->(f:Fact)
        WHERE f.status = 'SUPERSEDED' AND f.updated_at < datetime() - duration('P30D')
        DETACH DELETE f
        """
        await self.graph_repo.query(cleanup_query, {"user_id": user_id})
        logger.info("[Consolidator] Graph optimization completed.")

consolidator_service = ConsolidatorService()
