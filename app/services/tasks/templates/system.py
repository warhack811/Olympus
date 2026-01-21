"""
Mami AI - System Tasks
----------------------
Sistem görevleri: Sağlık kontrolü ve izleme.
"""

import logging
from datetime import datetime

from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger(__name__)


class BaseJob:
    """Tüm görevlerin temel sınıfı."""
    name: str = "base_job"
    schedule: str = "0 * * * *"
    
    async def run(self, **kwargs):
        raise NotImplementedError


class HealthCheckJob(BaseJob):
    """
    Sistem sağlık kontrolü.
    
    - Neo4j bağlantısı
    - Redis bağlantısı
    - Qdrant bağlantısı
    """
    
    name = "health_check"
    schedule = "*/5 * * * *"  # Her 5 dakikada
    
    async def run(self, graph_repo=None, vector_repo=None, **kwargs):
        """Sistem sağlığını kontrol et."""
        logger.info(f"[HealthCheckJob] Starting...")
        
        health = {
            "timestamp": datetime.now().isoformat(),
            "neo4j": "unknown",
            "qdrant": "unknown",
            "redis": "unknown"
        }
        
        # Neo4j check
        if graph_repo:
            try:
                await graph_repo.query("RETURN 1 as ok", {})
                health["neo4j"] = "healthy"
            except Exception as e:
                health["neo4j"] = f"unhealthy: {str(e)[:50]}"
        
        # Qdrant check
        if vector_repo:
            try:
                await vector_repo.health_check()
                health["qdrant"] = "healthy"
            except Exception as e:
                health["qdrant"] = f"unhealthy: {str(e)[:50]}"
        
        # Redis check
        try:
            from app.config import get_settings
            import redis
            settings = get_settings()
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                socket_timeout=2
            )
            r.ping()
            health["redis"] = "healthy"
        except Exception as e:
            health["redis"] = f"unhealthy: {str(e)[:50]}"
        
        # Telemetry
        telemetry.emit(
            EventType.SYSTEM,
            {"job": self.name, "health": health},
            component="tasks"
        )
        
        logger.info(f"[HealthCheckJob] Health: {health}")
        return health


class DueScannerJob(BaseJob):
    """
    Zamanı gelen görevleri tarar.
    """
    
    name = "due_scanner"
    schedule = "*/10 * * * *"  # Her 10 dakikada
    
    async def run(self, graph_repo=None, **kwargs):
        """Due task'ları tara ve bildirim oluştur."""
        logger.info(f"[DueScannerJob] Starting...")
        
        if not graph_repo:
            return {"scanned": 0}
        
        try:
            from app.services.brain.memory.prospective import scan_due_tasks, ensure_task_schema
            from app.services.brain.notificator import notification_gatekeeper
            
            # Tüm kullanıcıları bul
            await ensure_task_schema(graph_repo)
            users_query = """
            MATCH (u:User)-[:HAS_TASK]->(t:Task {status: 'OPEN'})
            WHERE t.due_at_dt IS NOT NULL
            RETURN DISTINCT u.id as user_id
            """
            
            users = await graph_repo.query(users_query, {})
            
            notifications_sent = 0
            for user in users or []:
                user_id = user["user_id"]
                due_tasks = await scan_due_tasks(user_id, graph_repo)
                
                for task in due_tasks:
                    allowed, notif_id = await notification_gatekeeper.emit_if_allowed(
                        user_id=user_id,
                        message=f"Hatırlatma: {task['text']}",
                        notification_type="task_reminder",
                        source="due_scanner"
                    )
                    if allowed:
                        notifications_sent += 1
            
            logger.info(f"[DueScannerJob] Sent {notifications_sent} notifications")
            return {"scanned": len(users or []), "notifications": notifications_sent}
            
        except Exception as e:
            logger.error(f"[DueScannerJob] Error: {e}")
            return {"scanned": 0, "error": str(e)}
