"""
Mami AI - Cognitive Tasks (Atlas Sovereign Edition)
---------------------------------------------------
Bilişsel işlemler için arka plan görevleri.

- EpisodeWorkerJob: Episode özetleme ve vektör gömme
- ConsolidationJob: Hafıza konsolidasyonu
"""

import logging
from typing import Optional
from datetime import datetime

from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)


class BaseJob:
    """Tüm görevlerin temel sınıfı."""
    
    name: str = "base_job"
    schedule: str = "*/30 * * * *"  # Her 30 dakikada bir
    
    async def run(self, **kwargs):
        raise NotImplementedError


class EpisodeWorkerJob(BaseJob):
    """
    Episode özetleme ve vektör gömme görevi.
    
    1. Bekleyen (PENDING) episode'ları bul
    2. LLM ile özetle
    3. Vektör embedding oluştur
    4. Qdrant'a kaydet
    """
    
    name = "episode_worker"
    schedule = "*/15 * * * *"  # Her 15 dakikada
    
    async def run(self, graph_repo=None, vector_repo=None, llm_provider=None, embedder=None, limit: int = 5):
        """Bekleyen episode'ları işle."""
        logger.info(f"[EpisodeWorkerJob] Starting...")
        
        telemetry.emit(
            EventType.SYSTEM,
            {"job": self.name, "status": "started"},
            component="tasks"
        )
        
        if not graph_repo:
            logger.warning("[EpisodeWorkerJob] No graph_repo, skipping")
            return {"processed": 0, "error": "no_graph_repo"}
        
        try:
            # 1. Bekleyen episode'ları bul
            query = """
            MATCH (e:Episode {status: 'PENDING'})
            RETURN e.id as id, e.session_id as session_id, e.user_id as user_id
            ORDER BY e.created_at ASC
            LIMIT $limit
            """
            
            pending = await graph_repo.query(query, {"limit": limit})
            
            if not pending:
                logger.info("[EpisodeWorkerJob] No pending episodes")
                return {"processed": 0}
            
            # 2. Her episode için işle
            from app.services.brain.memory.episode import finalize_episode, summarize_turns
            
            processed = 0
            for ep in pending:
                try:
                    # Turn'leri getir
                    turns_query = """
                    MATCH (e:Episode {id: $eid})-[:HAS_TURN]->(t:Turn)
                    RETURN t.role as role, t.content as content
                    ORDER BY t.created_at ASC
                    """
                    turns = await graph_repo.query(turns_query, {"eid": ep["id"]})
                    
                    # Özetle
                    summary = await summarize_turns(turns, llm_provider)
                    
                    # Finalize
                    result = await finalize_episode(
                        episode_id=ep["id"],
                        user_id=ep["user_id"],
                        session_id=ep["session_id"],
                        summary=summary,
                        graph_repo=graph_repo,
                        vector_repo=vector_repo,
                        embedder=embedder
                    )
                    
                    if result["status"] != "failed":
                        processed += 1
                        
                except Exception as e:
                    logger.error(f"[EpisodeWorkerJob] Episode {ep['id']} failed: {e}")
                    continue
            
            telemetry.emit(
                EventType.SYSTEM,
                {"job": self.name, "status": "completed", "processed": processed},
                component="tasks"
            )
            
            logger.info(f"[EpisodeWorkerJob] Processed {processed}/{len(pending)} episodes")
            return {"processed": processed}
            
        except Exception as e:
            logger.error(f"[EpisodeWorkerJob] Error: {e}")
            return {"processed": 0, "error": str(e)}


class ConsolidationJob(BaseJob):
    """
    Hafıza konsolidasyonu görevi.
    
    Düşük confidence fact'leri temizler veya güncellemez.
    """
    
    name = "consolidation_worker"
    schedule = "0 3 * * *"  # Her gün saat 3'te
    
    async def run(self, graph_repo=None, threshold: float = 0.3):
        """Düşük confidence fact'leri temizle."""
        logger.info(f"[ConsolidationJob] Starting...")
        
        if not graph_repo:
            return {"cleaned": 0}
        
        try:
            # Düşük confidence ilişkileri bul ve işaretle
            query = """
            MATCH ()-[r:FACT]->()
            WHERE r.confidence < $threshold
            AND r.status IS NULL OR r.status = 'ACTIVE'
            SET r.status = 'STALE'
            RETURN count(r) as cleaned
            """
            
            result = await graph_repo.query(query, {"threshold": threshold})
            cleaned = result[0]["cleaned"] if result else 0
            
            logger.info(f"[ConsolidationJob] Marked {cleaned} facts as STALE")
            return {"cleaned": cleaned}
            
        except Exception as e:
            logger.error(f"[ConsolidationJob] Error: {e}")
            return {"cleaned": 0, "error": str(e)}
