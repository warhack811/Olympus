import threading
import time
import os
import asyncio
import uuid
from datetime import datetime, timedelta

import schedule
from sqlmodel import select, col

from app.auth.user_manager import list_users
from app.core.logger import get_logger
from app.memory.store import cleanup_old_memories
from app.core.redis_client import get_redis

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# DISTRIBUTED LOCK PRIMITIVES (Token-Based & Safe)
# ---------------------------------------------------------------------------

async def acquire_leader_lock(lock_name: str, ttl: int = None) -> str | None:
    """
    Redis tabanlı distributed lock (Leader Election).
    FAIL-CLOSED: Redis yoksa kilit alınamaz, işlem yapılmaz.
    
    Returns:
        token (str): Kilit alındıysa token döner.
        None: Kilit alınamadıysa veya hata varsa.
    """
    try:
        redis = await get_redis()
        # Fail-Closed: Redis yoksa None dön (işlem yapma)
        if not redis:
            logger.error(f"[MAINTENANCE] Redis unavailable, cannot acquire lock: {lock_name}")
            return None

        if ttl is None:
            ttl = int(os.getenv("MAINTENANCE_LEADER_LOCK_TTL_SECONDS", "60"))

        token = str(uuid.uuid4())
        key = f"maintenance:leader:{lock_name}"
        
        # SET key token NX EX ttl
        # nx=True -> Sadece yoksa yaz
        # ex=ttl -> Süre dolunca sil
        if await redis.set(key, token, nx=True, ex=ttl):
            logger.debug(f"[MAINTENANCE] Lock acquired: {lock_name} ({token})")
            return token
            
        return None
        
    except Exception as e:
        logger.error(f"[MAINTENANCE] Lock acquire error: {e}")
        return None


async def release_leader_lock(lock_name: str, token: str):
    """
    Lock'ı güvenli şekilde (compare-and-delete) serbest bırakır.
    Sadece kendi aldığımız lock'ı sileriz.
    """
    if not token:
        return

    try:
        redis = await get_redis()
        if not redis:
            return
            
        key = f"maintenance:leader:{lock_name}"
        
        # Lua script: Get key, if value == token then del, else return 0
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await redis.eval(script, 1, key, token)
        logger.debug(f"[MAINTENANCE] Lock released: {lock_name}")
        
    except Exception as e:
        logger.error(f"[MAINTENANCE] Lock release error: {e}")


# ---------------------------------------------------------------------------
# MAINTENANCE TASKS
# ---------------------------------------------------------------------------

async def daily_memory_cleanup():
    """Her gece çalışır, tüm kullanıcıların eski hafızalarını temizler (Vektör sisteminde NO-OP)."""
    # Leader Lock Control
    token = await acquire_leader_lock("daily_memory_cleanup", ttl=300)
    if not token:
        logger.info("[MAINTENANCE] daily_memory_cleanup locked or skipped.")
        return

    try:
        logger.info("[MAINTENANCE] Günlük hafıza temizliği başlatılıyor...")
        users = list_users()
        total_removed = 0
    
        # DİKKAT: cleanup_old_memories fonksiyonu, yeni ChromaDB mimarisinde
        # index tabanlı çalıştığı için artık hiçbir işlem yapmaz (NO-OP).
    
        for user in users:
            removed = await cleanup_old_memories(user.username)
            total_removed += removed
    
        logger.info(f"[MAINTENANCE] Temizlik tamamlandı. {total_removed} kayıt silindi (çoğu NO-OP).")
    finally:
        await release_leader_lock("daily_memory_cleanup", token)


async def episodic_memory_worker():
    """Periyodik olarak bekleyen oturumları özetler ve hafızayı günceller."""
    # Leader Lock Control
    token = await acquire_leader_lock("episodic_memory_worker", ttl=600)
    if not token:
        logger.debug("[MAINTENANCE] episodic_memory_worker is locked by another instance. Skipping.")
        return

    try:
        from app.services.brain.cognition_service import cognition_service
        logger.info("[MAINTENANCE] Episodik hafıza yönetimi başlatılıyor...")
        
        # Son 24 saatte aktif olan oturumları işle
        processed = await cognition_service.process_pending_sessions(lookback_hours=24)
        
        logger.info(f"[MAINTENANCE] Episodik hafıza güncellendi. {processed} oturum işlendi.")
    except Exception as e:
        logger.error(f"[MAINTENANCE] episodic_memory_worker failed: {e}")
    finally:
        await release_leader_lock("episodic_memory_worker", token)


async def reflection_worker():
    """Analiz edilmiş anılar üzerinde kognitif çıkarım (Reflection) yapar."""
    token = await acquire_leader_lock("reflection_worker", ttl=600)
    if not token: return

    try:
        from app.services.brain.reflection import reflection_service
        from app.core.database import get_session
        from app.core.models import User
        
        logger.info("[MAINTENANCE] Kognitif çıkarım (Reflection) süreci başlatılıyor...")
        
        with get_session() as session:
            users = session.exec(select(User)).all()
            for user in users:
                await reflection_service.reflect_on_user(str(user.id))
                
        logger.info("[MAINTENANCE] Reflection süreci tamamlandı.")
    except Exception as e:
        logger.error(f"[MAINTENANCE] reflection_worker failed: {e}")
    finally:
        await release_leader_lock("reflection_worker", token)


def start_maintenance_scheduler():
    """Bakım görevlerini başlatır."""
    
    # Yeni bir event loop oluştur
    maintenance_loop = asyncio.new_event_loop()

    def run_scheduler():
        asyncio.set_event_loop(maintenance_loop)
        
        # Schedule wrappers
        def daily_cleanup_wrapper():
            maintenance_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(daily_memory_cleanup())
            )

        def job_cleanup_wrapper():
            maintenance_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(cleanup_stuck_image_jobs())
            )

        def memory_worker_wrapper():
            maintenance_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(episodic_memory_worker())
            )

        def reflection_worker_wrapper():
            maintenance_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(reflection_worker())
            )

        # Register schedules
        schedule.every().day.at("03:00").do(daily_cleanup_wrapper)
        schedule.every(10).minutes.do(job_cleanup_wrapper)
        schedule.every(30).minutes.do(memory_worker_wrapper)  # Was 15, now 30 to reduce API pressure
        schedule.every(2).hours.do(reflection_worker_wrapper)  # Was 1, now 2 hours

        logger.info("[MAINTENANCE] Bakım scheduler (Background Thread) başlatıldı.")
        
        # Start the loop in this thread
        maintenance_loop.run_forever()

    def tick_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)

    # Scheduler thread (Blocking schedule.run_pending)
    threading.Thread(target=tick_scheduler, daemon=True, name="maint-sched").start()
    
    # Worker thread (Running the asyncio loop)
    threading.Thread(target=run_scheduler, daemon=True, name="maint-worker").start()


async def cleanup_stuck_image_jobs():
    """
    Belirli bir süredir yanıt vermeyen (heartbeat almayan) görsel işlerini 'error' durumuna çeker.
    """
    # 1. Lock Acquisition (Fail-Closed)
    token = await acquire_leader_lock("stuck_job_cleanup", ttl=120)
    if not token:
        logger.debug("[MAINTENANCE] Job cleanup locked. Skipping.")
        return

    from app.core.database import get_session
    from app.core.models import Message
    
    try:
        # Configurable Timeout (default 30 mins)
        stuck_minutes = float(os.getenv("IMAGE_JOB_STUCK_AFTER_MINUTES", "30.0"))
        now = datetime.utcnow()
        threshold = now - timedelta(minutes=stuck_minutes)
        min_lookback = now - timedelta(hours=24) 
        
        cleanup_count = 0
        
        with get_session() as session:
            # Find candidate messages
            stmt = select(Message).where(
                Message.created_at >= min_lookback,
                Message.created_at <= now
            )
            messages = session.exec(stmt).all()
            
            for msg in messages:
                if not msg.extra_metadata:
                    continue
                    
                meta = msg.extra_metadata or {}
                
                # Filter: Type=image AND Status in active states
                if meta.get("type") == "image" and meta.get("status") in ["queued", "processing"]:
                    
                    # Smart Check: Use 'last_activity_at' -> 'created_at' fallback
                    last_activity = msg.created_at # Default fallback
                    
                    last_activity_str = meta.get("last_activity_at")
                    if last_activity_str and isinstance(last_activity_str, str):
                        try:
                            # Handle 'Z' if present for py < 3.11 compatibility or just robustness
                            clean_str = last_activity_str.replace("Z", "+00:00")
                            last_activity = datetime.fromisoformat(clean_str)
                            
                            # Normalize TZ: Convert to UTC then make naive
                            # This handles +03:00 etc correctly by shifting time to UTC
                            if last_activity.tzinfo is not None:
                                from datetime import timezone
                                last_activity = last_activity.astimezone(timezone.utc).replace(tzinfo=None)
                                
                        except ValueError:
                            pass # Fallback to created_at
                        
                    # Decision
                    if last_activity < threshold:
                        job_id = meta.get("job_id", "unknown")
                        logger.warning(f"[MAINTENANCE] Stuck job detected: {job_id} (Last Active: {last_activity} < {threshold})")
                        
                        # Update Metadata
                        new_meta = meta.copy()
                        new_meta["status"] = "error"
                        new_meta["error"] = "Zaman aşımı (Stuck Job Auto-Cleanup)"
                        new_meta["completed_at"] = now.isoformat()
                        # Removing processing status
                        
                        # Update Message
                        msg.extra_metadata = new_meta
                        session.add(msg)
                        cleanup_count += 1
            
            if cleanup_count > 0:
                session.commit()
                logger.info(f"[MAINTENANCE] Cleared {cleanup_count} stuck image jobs.")
                
    except Exception as e:
        logger.error(f"[MAINTENANCE] cleanup_stuck_image_jobs failed: {e}")
    finally:
        await release_leader_lock("stuck_job_cleanup", token)

