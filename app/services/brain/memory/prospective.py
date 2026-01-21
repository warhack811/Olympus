"""
Mami AI - Prospective Memory Service (Atlas Sovereign Edition)
--------------------------------------------------------------
Gelecek hatırlatma/task kayıt sistemi.

Temel Sorumluluklar:
1. Task Oluşturma: Türkçe tarih ayrıştırma ile Neo4j Task düğümü oluşturma
2. Due Scanning: Zamanı gelmiş görevleri tarama
3. Task Yönetimi: Tamamlama, listeleme, iptal
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)

_schema_warmed = False


async def _ensure_task_property_keys(graph_repo = None) -> None:
    global _schema_warmed
    if _schema_warmed or not graph_repo:
        return
    query = """
    MERGE (k:__Schema {name: 'task_properties'})
    SET k.due_at_dt = datetime(),
        k.last_notified_at = datetime()
    WITH k
    DETACH DELETE k
    """
    try:
        await graph_repo.query(query, {})
        _schema_warmed = True
    except Exception as e:
        logger.warning(f"[ProspectiveService] Schema warmup failed: {e}")


async def create_task(
    user_id: str,
    raw_text: str,
    due_at: Optional[str] = None,
    source_turn_id: Optional[str] = None,
    graph_repo = None
) -> Optional[str]:
    """
    Prospective task oluştur (Neo4j Task node).
    
    Args:
        user_id: Kullanıcı ID
        raw_text: Orijinal mesaj ("Yarın saat 10'da toplantı")
        due_at: Hedef tarih/zaman (doğal dil veya ISO)
        source_turn_id: Bu task'ı yaratan turn ID
        graph_repo: Graph repository (opsiyonel)
    
    Returns:
        Task ID (UUID) veya None
    """
    task_id = str(uuid.uuid4())[:8]
    
    # Telemetry
    telemetry.emit(
        EventType.MEMORY_OP,
        {"op": "create_task", "user_id": user_id, "task_id": task_id},
        component="prospective"
    )
    
    # Parse due_at with dateparser
    due_at_dt = None
    if due_at:
        try:
            import dateparser
            parsed = dateparser.parse(
                due_at,
                languages=['tr'],
                settings={'PREFER_DATES_FROM': 'future'}
            )
            if parsed:
                due_at_dt = parsed.isoformat()
        except ImportError:
            logger.warning("[ProspectiveService] dateparser not installed")
        except Exception as e:
            logger.warning(f"[ProspectiveService] Date parsing error: {e}")
    
    # Neo4j query
    query = """
    MERGE (u:User {id: $uid})
    CREATE (t:Task {
        id: $task_id,
        user_id: $uid,
        created_at: datetime(),
        status: 'OPEN',
        raw_text: $raw_text,
        source_turn_id: $source_turn_id,
        due_at_raw: $due_at_raw,
        due_at_dt: CASE WHEN $due_at_dt IS NOT NULL THEN datetime($due_at_dt) ELSE null END,
        last_notified_at: null,
        notified_count: 0
    })
    MERGE (u)-[:HAS_TASK]->(t)
    RETURN t.id as task_id
    """
    
    try:
        if graph_repo:
            await graph_repo.query(query, {
                "uid": user_id,
                "task_id": task_id,
                "raw_text": raw_text,
                "source_turn_id": source_turn_id,
                "due_at_raw": due_at,
                "due_at_dt": due_at_dt
            })
        
        logger.info(f"[ProspectiveService] Task created: {task_id}")
        return task_id
        
    except Exception as e:
        logger.error(f"[ProspectiveService] Task creation error: {e}")
        telemetry.emit(
            EventType.ERROR,
            {"op": "create_task_error", "error": str(e)},
            component="prospective"
        )
        return None


async def ensure_task_schema(graph_repo = None) -> None:
    await _ensure_task_property_keys(graph_repo)


async def scan_due_tasks(user_id: str, graph_repo = None) -> List[Dict]:
    """
    Kullanıcının zamanı gelen görevlerini tarar.
    
    Args:
        user_id: Kullanıcı ID
        graph_repo: Graph repository
    
    Returns:
        Due tasks list
    """
    await _ensure_task_property_keys(graph_repo)
    query = """
    MATCH (u:User {id: $uid})-[:HAS_TASK]->(t:Task {status: 'OPEN'})
    WHERE t.due_at_dt IS NOT NULL 
      AND t.due_at_dt <= datetime()
      AND (t.last_notified_at IS NULL OR t.last_notified_at < datetime() - duration('PT60M'))
    RETURN t.id as id, t.raw_text as text, t.due_at_raw as due_raw
    """
    
    try:
        if graph_repo:
            result = await graph_repo.query(query, {"uid": user_id})
            return result if result else []
        return []
    except Exception as e:
        logger.error(f"[ProspectiveService] Due scan error: {e}")
        return []


async def list_open_tasks(user_id: str, limit: int = 10, graph_repo = None) -> List[Dict]:
    """
    Kullanıcının açık task'lerini listele.
    """
    query = """
    MATCH (u:User {id: $uid})-[:HAS_TASK]->(t:Task {status: 'OPEN'})
    RETURN t.id as id, t.raw_text as text, t.created_at as created, t.due_at_raw as due_raw
    ORDER BY t.created_at DESC
    LIMIT $limit
    """
    
    try:
        if graph_repo:
            result = await graph_repo.query(query, {"uid": user_id, "limit": limit})
            return result if result else []
        return []
    except Exception as e:
        logger.warning(f"[ProspectiveService] List tasks error: {e}")
        return []


async def mark_task_done(user_id: str, task_id: str, graph_repo = None) -> bool:
    """
    Task'ı tamamlandı olarak işaretle.
    """
    query = """
    MATCH (u:User {id: $uid})-[:HAS_TASK]->(t:Task {id: $task_id})
    SET t.status = 'DONE', t.completed_at = datetime()
    RETURN count(t) as updated
    """
    
    try:
        if graph_repo:
            result = await graph_repo.query(query, {"uid": user_id, "task_id": task_id})
            success = result[0]["updated"] > 0 if result else False
            
            if success:
                telemetry.emit(
                    EventType.MEMORY_OP,
                    {"op": "task_done", "task_id": task_id},
                    component="prospective"
                )
            return success
        return False
    except Exception as e:
        logger.error(f"[ProspectiveService] Mark done error: {e}")
        return False


class ProspectiveService:
    """Prospective Memory Service singleton wrapper."""
    
    def __init__(self, graph_repo = None):
        self.graph_repo = graph_repo
    
    async def create_task(self, user_id: str, raw_text: str, due_at: str = None) -> Optional[str]:
        return await create_task(user_id, raw_text, due_at, graph_repo=self.graph_repo)
    
    async def scan_due_tasks(self, user_id: str) -> List[Dict]:
        return await scan_due_tasks(user_id, graph_repo=self.graph_repo)
    
    async def list_open_tasks(self, user_id: str, limit: int = 10) -> List[Dict]:
        return await list_open_tasks(user_id, limit, graph_repo=self.graph_repo)
    
    async def mark_task_done(self, user_id: str, task_id: str) -> bool:
        return await mark_task_done(user_id, task_id, graph_repo=self.graph_repo)


prospective_service = ProspectiveService()
