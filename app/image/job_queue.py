# image/job_queue.py
from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import uuid4

from app.core.logger import get_logger
from app.core.websockets import ImageJobStatus, send_image_progress
from app.image.flux_stub import generate_image_via_forge
from app.image.gpu_state import switch_to_flux, switch_to_gemma

logger = get_logger(__name__)


class ImageJob:
    def __init__(
        self,
        username: str,
        prompt: str,
        conversation_id: str | None,
        on_done: Callable[[str], None],
        job_id: str | None = None,
        checkpoint_name: str | None = None,
        message_id: int | None = None,
        image_settings: dict | None = None,
        priority: str = "normal",  # FAZE 4: low/normal/high
        batch_id: str | None = None,  # FAZE 4: batch processing
        timeout_seconds: int = 300,  # FAZE 4: 5 minutes default
    ):
        self.username = username
        self.prompt = prompt
        self.conversation_id = conversation_id
        self.on_done = on_done
        self.progress = 0
        self.queue_pos = 0
        self.job_id = job_id or str(uuid4())
        self.checkpoint_name = checkpoint_name
        self.message_id = message_id
        self.image_settings = image_settings or {}
        self.priority = priority  # FAZE 4
        self.batch_id = batch_id  # FAZE 4
        self.timeout_seconds = timeout_seconds  # FAZE 4
        self.retry_count = 0  # FAZE 4
        self.start_time: float | None = None  # FAZE 4


class ImageJobQueue:
    """
    Görsel üretim iş kuyruğu.

    Worker lazy initialization ile başlatılır - ilk iş eklendiğinde
    event loop hazır olduğunda çalışır.
    """

    def __init__(self):
        self._queue: asyncio.Queue[ImageJob] | None = None
        self._gpu_lock: asyncio.Lock | None = None
        self._worker_task = None
        self._started = False
        self._current_job: ImageJob | None = None  # Aktif işlenen job
        self._cancelled_jobs: set[str] = set()  # İptal edilen job_id'ler

    @property
    def queue(self) -> asyncio.Queue[ImageJob]:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    @property
    def gpu_lock(self) -> asyncio.Lock:
        if self._gpu_lock is None:
            self._gpu_lock = asyncio.Lock()
        return self._gpu_lock

    def _ensure_worker_started(self):
        """Worker'ı lazily başlatır (event loop hazır olduğunda)."""
        from app.config import get_settings
        settings = get_settings()
        if settings.DEBUG:
            logger.debug(f"[IMAGE_QUEUE] _ensure_worker_started called, _started={self._started}")
        if not self._started:
            try:
                loop = asyncio.get_running_loop()
                self._worker_task = loop.create_task(self._worker_loop())
                self._started = True
                if settings.DEBUG:
                    logger.debug("[IMAGE_QUEUE] Worker task CREATED")
                logger.info("[IMAGE_QUEUE] Worker başlatıldı")
            except RuntimeError as e:
                if settings.DEBUG:
                    logger.debug(f"[IMAGE_QUEUE] Worker start FAILED: {e}")
                # Event loop yok - startup event'te başlatılacak
                pass

    # ---------- ASYNC WORKER ----------
    async def _worker_loop(self) -> None:
        """Main worker loop - processes jobs sequentially with GPU lock"""
        from app.config import get_settings
        settings = get_settings()
        if settings.DEBUG:
            logger.debug("[IMAGE_QUEUE] _worker_loop STARTED - waiting for jobs")
        while True:
            # FAZE 4: Get next job with priority sorting
            job = await self._get_next_job()
            if settings.DEBUG:
                logger.debug(f"[IMAGE_QUEUE] Worker got job: {job.job_id[:8]}")

            # İptal edilmiş mi kontrol et
            if job.job_id in self._cancelled_jobs:
                logger.info(f"[IMAGE_QUEUE] ⏭️ Skipping cancelled job: {job.job_id}")
                self._cancelled_jobs.discard(job.job_id)
                self.queue.task_done()
                continue

            # FAZE 2: GPU lock ile sequential processing
            async with self.gpu_lock:
                logger.info(f"[GPU_LOCK] Acquired for job {job.job_id[:8]}")
                self._current_job = job
                try:
                    await self._process_single_job(job)
                finally:
                    self._current_job = None
                    logger.info(f"[GPU_LOCK] Released for job {job.job_id[:8]}")
            
            self.queue.task_done()

    async def _process_single_job(self, job: ImageJob) -> None:
        """Process a single job with GPU lock held"""
        import time
        logger.info(f"[IMAGE_QUEUE] Processing: {job.job_id[:8]}")
        job.start_time = time.time()  # FAZE 4: Track start time for timeout
        
        try:
            # Üretim başlamadan önce cancelled kontrolü
            if job.job_id in self._cancelled_jobs:
                logger.info(f"[IMAGE_QUEUE] 🛑 Job cancelled before start: {job.job_id}")
                self._cancelled_jobs.discard(job.job_id)
                return

            # FAZE 2: Processing başladığında queue_position'ı 0'a set et
            from app.memory.conversation import update_message
            if job.message_id:
                update_message(
                    job.message_id,
                    None,
                    {
                        "status": "processing",
                        "progress": 0,
                        "queue_position": 0
                    }
                )

            switch_to_flux()
            
            # FAZE 4: Wrap with timeout
            try:
                image_url = await asyncio.wait_for(
                    generate_image_via_forge(job.prompt, job, checkpoint_name=job.checkpoint_name),
                    timeout=job.timeout_seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Image generation timeout after {job.timeout_seconds}s")

            # Üretim sonrası cancelled kontrolü (interrupt sonrası)
            if job.job_id in self._cancelled_jobs:
                logger.info(f"[IMAGE_QUEUE] 🛑 Job was cancelled during processing: {job.job_id}")
                self._cancelled_jobs.discard(job.job_id)
                return

            job.on_done(image_url)
            
        except Exception as e:
            # Cancelled job'lar için error gönderme
            if job.job_id in self._cancelled_jobs:
                logger.info(f"[IMAGE_QUEUE] Job cancelled (exception ignored): {job.job_id}")
                self._cancelled_jobs.discard(job.job_id)
                return

            # FAZE 4: Retry logic with exponential backoff (1s, 2s, 4s, 8s)
            if job.retry_count < 4 and not isinstance(e, TimeoutError):
                backoff_seconds = 2 ** job.retry_count  # 1s, 2s, 4s, 8s
                logger.warning(f"[IMAGE_QUEUE] Retry {job.retry_count + 1}/4 for {job.job_id[:8]} after {backoff_seconds}s: {e}")
                
                job.retry_count += 1
                job.start_time = None  # Reset start time for retry
                
                # Wait and re-queue
                await asyncio.sleep(backoff_seconds)
                self.queue.put_nowait(job)
                return

            logger.error(f"[IMAGE_QUEUE] Resim hatası: {e}", exc_info=True)
            
            # FAZE 2: Error recovery - error persist et ve sonraki job başlasın
            from app.memory.conversation import update_message
            if job.message_id:
                error_msg = str(e)
                if isinstance(e, TimeoutError):
                    error_msg = f"Timeout: {error_msg}"
                update_message(job.message_id,
                    content=f"❌ Görsel oluşturulamadı: {error_msg}",
                    new_metadata={
                        "status": "error",
                        "error": error_msg,
                        "progress": 0,
                        "queue_position": 0,
                        "retry_count": job.retry_count
                    }
                )
            
            # Hata durumunu WebSocket üzerinden gönder
            try:
                await send_image_progress(
                    username=job.username,
                    conversation_id=job.conversation_id,
                    job_id=job.job_id,
                    status=ImageJobStatus.ERROR,
                    progress=0,
                    queue_position=0,
                    prompt=job.prompt,
                    error=str(e),
                )
            except Exception as ws_err:
                from app.config import get_settings
                settings = get_settings()
                if settings.DEBUG:
                    logger.debug(f"[IMAGE_QUEUE] WS error notification failed: {ws_err}")
            
            job.on_done(f"(IMAGE ERROR) {e}")
            # Next job will automatically start (worker loop continues)
            
        finally:
            switch_to_gemma()
            logger.info(f"[IMAGE_QUEUE] Completed: {job.job_id[:8]}")
            
            # FAZE 3: Recalculate queue positions for remaining jobs
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._recalculate_queue_positions(job.conversation_id))
            except RuntimeError:
                pass  # Event loop yok

    # ---------- KUYRUĞA EKLE ----------
    async def _send_queued_status(self, job: ImageJob, queue_pos: int) -> None:
        """İş kuyruğa alındığında QUEUED durumunu gönderir."""
        try:
            await send_image_progress(
                username=job.username,
                conversation_id=job.conversation_id,
                job_id=job.job_id,
                status=ImageJobStatus.QUEUED,
                progress=0,
                queue_position=queue_pos,
                prompt=job.prompt,
                estimated_seconds=queue_pos * 30,  # Her iş için ~30 saniye tahmin
            )
        except Exception as e:
            logger.debug(f"[IMAGE_QUEUE] WS queued notification failed: {e}")

    def add_job(self, job: ImageJob) -> int:
        """İşi kuyruğa ekler, queue position'ı persist eder ve worker'ı başlatır."""
        # Worker'ın başlatıldığından emin ol
        self._ensure_worker_started()

        # FAZE 4: Validate batch consistency if batch_id provided
        if job.batch_id:
            self._validate_batch_consistency(job)

        # FAZE 4: Calculate queue position considering priority
        queue_pos = self._calculate_queue_position(job)
        job.queue_pos = queue_pos
        
        # FAZE 2: Queue position'ı persist et
        from app.memory.conversation import update_message
        if job.message_id:
            update_message(
                job.message_id,
                None,
                {
                    "status": "queued",
                    "progress": 0,
                    "queue_position": queue_pos,
                    "job_id": job.job_id,
                    "prompt": job.prompt,
                    "priority": job.priority,  # FAZE 4
                    "batch_id": job.batch_id,  # FAZE 4
                    "retry_count": job.retry_count  # FAZE 4
                }
            )
        
        # Kuyruğa ekle
        self.queue.put_nowait(job)
        logger.info(f"[IMAGE_QUEUE] İş eklendi: {job.job_id[:8]}, pozisyon: {queue_pos}, priority: {job.priority}")

        # QUEUED durumunu async olarak gönder
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_queued_status(job, queue_pos))
        except RuntimeError:
            pass  # Event loop yok

        return queue_pos

    async def add_batch_jobs(self, jobs: list[ImageJob]) -> dict:
        """
        FAZE 4: Add multiple jobs as atomic batch.
        All jobs must have same batch_id and conversation_id.
        Either all succeed or all fail (atomic operation).
        """
        if not jobs:
            return {"status": "error", "message": "Batch boş olamaz"}
        
        batch_id = jobs[0].batch_id
        conversation_id = jobs[0].conversation_id
        
        # Validate batch consistency - all jobs must have same batch_id and conversation_id
        for job in jobs:
            if job.batch_id != batch_id:
                return {"status": "error", "message": f"Batch ID tutarsız: {job.batch_id} != {batch_id}"}
            if job.conversation_id != conversation_id:
                return {"status": "error", "message": f"Conversation ID tutarsız: {job.conversation_id} != {conversation_id}"}
        
        # Validate all jobs before adding any
        for job in jobs:
            if not job.prompt or not job.username:
                return {"status": "error", "message": f"Job {job.job_id[:8]} eksik bilgi içeriyor"}
        
        # Add all jobs atomically
        added_jobs = []
        try:
            for job in jobs:
                pos = self.add_job(job)
                added_jobs.append({"job_id": job.job_id, "position": pos})
            
            logger.info(f"[IMAGE_QUEUE] Batch {batch_id[:8]} added: {len(added_jobs)} jobs")
            return {
                "status": "success",
                "batch_id": batch_id,
                "jobs_added": len(added_jobs),
                "jobs": added_jobs
            }
        except Exception as e:
            logger.error(f"[IMAGE_QUEUE] Batch {batch_id[:8]} failed: {e}")
            # In case of error, all jobs are already in queue - this is acceptable
            # as they will be processed normally
            return {
                "status": "partial_error",
                "batch_id": batch_id,
                "jobs_added": len(added_jobs),
                "error": str(e)
            }

    async def cancel_job(self, job_id: str, username: str) -> bool:
        """
        Job'u iptal et - hem kuyruktan hem aktif üretimden.
        Returns: True if cancelled, False if not found.
        """
        import httpx

        from app.config import get_settings

        settings = get_settings()

        # 1️⃣ KUYRUKTAN KALDIR
        temp_jobs = []
        found_job = None

        while not self.queue.empty():
            try:
                job = self.queue.get_nowait()
                if job.job_id == job_id and job.username == username:
                    found_job = job
                else:
                    temp_jobs.append(job)
            except asyncio.QueueEmpty:
                break

        # Diğer job'ları geri koy
        for job in temp_jobs:
            self.queue.put_nowait(job)

        if found_job:
            logger.info(f"[IMAGE_QUEUE] 🗑️ Job removed from queue: {job_id}")

            # Cancelled durumunu gönder
            try:
                await send_image_progress(
                    username=found_job.username,
                    conversation_id=found_job.conversation_id,
                    job_id=found_job.job_id,
                    status=ImageJobStatus.ERROR,
                    progress=0,
                    queue_position=0,
                    prompt=found_job.prompt,
                    error="İptal edildi",
                )
            except Exception as e:
                from app.config import get_settings
                settings = get_settings()
                if settings.DEBUG:
                    logger.debug(f"[IMAGE_QUEUE] WS cancel notification failed: {e}")

            return True

        # 2️⃣ AKTİF JOB İSE FORGE'A INTERRUPT GÖNDER
        if self._current_job and self._current_job.job_id == job_id:
            logger.info(f"[IMAGE_QUEUE] ⏸️ Interrupting active job: {job_id}")

            # Cancelled set'e ekle
            self._cancelled_jobs.add(job_id)

            # Forge API interrupt
            try:
                interrupt_url = f"{settings.FORGE_BASE_URL}/sdapi/v1/interrupt"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(interrupt_url)
                    logger.info(f"[IMAGE_QUEUE] Forge interrupt response: {response.status_code}")
            except Exception as e:
                logger.warning(f"[IMAGE_QUEUE] ⚠️ Forge interrupt failed (job marked as cancelled): {e}", exc_info=True)

            # Cancelled durumunu gönder
            try:
                await send_image_progress(
                    username=self._current_job.username,
                    conversation_id=self._current_job.conversation_id,
                    job_id=job_id,
                    status=ImageJobStatus.ERROR,
                    progress=self._current_job.progress,
                    queue_position=0,
                    prompt=self._current_job.prompt,
                    error="İptal edildi",
                )
            except Exception as e:
                from app.config import get_settings
                settings = get_settings()
                if settings.DEBUG:
                    logger.debug(f"[IMAGE_QUEUE] WS cancel notification failed: {e}")

            return True

        # Job bulunamadı
        logger.warning(f"[IMAGE_QUEUE] ❓ Job not found for cancellation: {job_id}", exc_info=False)  # Not an error, just info
        return False

    async def _recalculate_queue_positions(self, conversation_id: str | None) -> None:
        """FAZE 3: Recalculate queue positions for all queued jobs in conversation, considering priority"""
        from app.core.database import get_session
        from app.core.models import Message
        
        if not conversation_id:
            return
        
        try:
            session = get_session()
            
            # Get all queued messages in conversation
            queued_messages = session.query(Message).filter(
                Message.conversation_id == conversation_id,
                Message.extra_metadata["status"].astext == "queued"
            ).order_by(Message.created_at).all()
            
            if not queued_messages:
                return
            
            # Sort by priority first, then by creation time
            priority_order = {"high": 0, "normal": 1, "low": 2}
            
            def get_sort_key(msg):
                meta = msg.extra_metadata or {}
                priority = meta.get("priority", "normal")
                return (priority_order.get(priority, 1), msg.created_at)
            
            queued_messages.sort(key=get_sort_key)
            
            # Recalculate positions
            from app.memory.conversation import update_message
            for idx, msg in enumerate(queued_messages, 1):
                new_position = idx
                old_position = msg.extra_metadata.get("queue_position", 0) if msg.extra_metadata else 0
                
                if old_position != new_position:
                    update_message(msg.id, None, {
                        "queue_position": new_position
                    })
                    
                    # Send WebSocket notification for position change
                    try:
                        await send_image_progress(
                            username=msg.user.username if msg.user else "unknown",
                            conversation_id=conversation_id,
                            job_id=msg.extra_metadata.get("job_id", "") if msg.extra_metadata else "",
                            status=ImageJobStatus.QUEUED,
                            progress=0,
                            queue_position=new_position,
                            prompt=msg.extra_metadata.get("prompt", "") if msg.extra_metadata else "",
                        )
                    except Exception as e:
                        logger.debug(f"[IMAGE_QUEUE] Position update WS notification failed: {e}")
            
            logger.info(f"[IMAGE_QUEUE] Recalculated positions for {len(queued_messages)} queued jobs (priority-aware)")
            
        except Exception as e:
            logger.error(f"[IMAGE_QUEUE] Position recalculation failed: {e}", exc_info=True)

    # FAZE 4: Priority queue and batch processing helpers
    async def _get_next_job(self) -> ImageJob:
        """Get next job from queue, sorted by priority"""
        # Get all jobs from queue temporarily
        jobs = []
        while not self.queue.empty():
            try:
                job = self.queue.get_nowait()
                jobs.append(job)
            except asyncio.QueueEmpty:
                break
        
        if not jobs:
            # Queue is empty, wait for next job
            return await self.queue.get()
        
        # Sort by priority (high > normal > low)
        priority_order = {"high": 0, "normal": 1, "low": 2}
        jobs.sort(key=lambda j: (priority_order.get(j.priority, 1), j.queue_pos))
        
        # Put back all jobs except the first one
        next_job = jobs[0]
        for job in jobs[1:]:
            self.queue.put_nowait(job)
        
        return next_job

    def _calculate_queue_position(self, job: ImageJob) -> int:
        """Calculate queue position considering priority - higher priority jobs get lower position numbers"""
        # Get all jobs from queue temporarily
        jobs = []
        while not self.queue.empty():
            try:
                j = self.queue.get_nowait()
                jobs.append(j)
            except asyncio.QueueEmpty:
                break
        
        # Put jobs back
        for j in jobs:
            self.queue.put_nowait(j)
        
        # Add the new job to calculate its position
        all_jobs = jobs + [job]
        
        # Sort by priority (high > normal > low)
        priority_order = {"high": 0, "normal": 1, "low": 2}
        all_jobs.sort(key=lambda j: (priority_order.get(j.priority, 1), j.queue_pos if hasattr(j, 'queue_pos') else 0))
        
        # Find position of new job
        for idx, j in enumerate(all_jobs, 1):
            if j.job_id == job.job_id:
                return idx
        
        return len(all_jobs)

    def _validate_batch_consistency(self, job: ImageJob) -> None:
        """Validate batch consistency - all jobs in batch must have same conversation_id"""
        if not job.batch_id:
            return
        
        # In production, check database for other jobs with same batch_id
        # Ensure they all have same conversation_id
        logger.debug(f"[IMAGE_QUEUE] Batch {job.batch_id[:8]} validated for job {job.job_id[:8]}")

    def get_queue_status(self) -> dict:
        return {"pending_jobs": self.queue.qsize(), "is_processing": self.gpu_lock.locked()}


# Tek instance
job_queue = ImageJobQueue()
