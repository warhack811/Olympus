import asyncio
import base64
import json
import logging
import os
import time
from pathlib import Path

import aiohttp
import httpx
import redis.asyncio as redis

# Mami AI Config import
from app.config import get_settings
from app.memory.conversation import update_message

import sys

# Logger Ayarı
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AtlasWorker")

# Windows için Event Loop Fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class AtlasLocalWorker:
    def __init__(self):
        self.redis_client = None
        self.gpu_lock = asyncio.Lock()  # Sequential GPU processing
        self.processing_queue = asyncio.Queue()  # Task queue for sequential processing
        self.is_processing = False  # Flag to track if currently processing
        self.total_queued_tasks = 0  # Track total tasks queued (for position calculation)
        s = get_settings()
        self.forge_url = s.FORGE_BASE_URL.rstrip("/") + s.FORGE_TXT2IMG_PATH
        self.progress_url = f"{s.FORGE_BASE_URL.rstrip('/')}/sdapi/v1/progress"
        self.upload_url = f"{s.ATLAS_API_BASE_URL.rstrip('/')}/api/v1/user/images/internal-upload"
        self.worker_token = s.INTERNAL_UPLOAD_TOKEN
        self.is_running = True
        self.queue_processor_task = None  # Task for queue processor

    async def connect_redis(self):
        """Upstash Redis'e bağlanır."""
        try:
            s = get_settings()
            url = s.get_redis_url(s.REDIS_DB_QUEUE)
            # SSL_CERT_REQS=none (Upstash Fix)
            self.redis_client = redis.from_url(url, decode_responses=True, ssl_cert_reqs=None)
            logger.info("Connected to Upstash Redis (SSL: none)")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def publish_status(
        self,
        job_id,
        status,
        progress=0,
        message_id=None,
        conv_id=None,
        prompt=None,
        image_url=None,
        error=None,
        user_id=None,
        username=None,
        queue_position=None,
    ):
        """Upstash üzerinden Cloud Server'a durum bilgisi gönderir."""
        if not self.redis_client:
            await self.connect_redis()
            
        # [FIX] Username is critical for WebSocket delivery.
        final_username = username
        if not final_username and user_id:
             final_username = str(user_id)

        payload = {
            "type": "image_progress", 
            "job_id": job_id,
            "username": final_username, 
            "user_id": str(user_id) if user_id else None,
            "status": status,
            "progress": progress,
            "message_id": str(message_id) if message_id else None,
            "conversation_id": str(conv_id) if conv_id else None,
            "prompt": prompt,
            "image_url": image_url,
            "error": error,
            "queue_position": queue_position or 0,
        }
        
        if os.getenv("SMOKE_TEST_ENABLED", "false").lower() == "true":
            logger.info(f"[E2E_SMOKE] WORKER_UPDATE: job_id={job_id} status={status}")
            
        try:
            await self.redis_client.publish("atlas_image_status_stream", json.dumps(payload))
            logger.info(f"[WORKER_PUBLISH] Published to Redis: job_id={job_id[:8]}, status={status}, username={final_username}, message_id={message_id}, queue_pos={queue_position}")
        except Exception as e:
            logger.warning(f"Status publish failed: {e}")

    async def poll_forge_progress(self, job_id, message_id, conv_id, user_id=None, username=None):
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(self.progress_url, timeout=2) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            progress = int(data.get("progress", 0) * 100)
                            # Publishing progress with queue_position=0 (currently processing)
                            await self.publish_status(job_id, "processing", progress, message_id, conv_id, queue_position=0, user_id=user_id, username=username)
                            if progress >= 100: break
                except Exception:
                    pass
                await asyncio.sleep(1)

    async def generate_and_upload(self, task):
        job_id = task["job_id"]
        prompt = task["prompt"]
        user_id = task.get("user_id")
        username = task.get("username")
        message_id = task.get("message_id")
        conv_id = task.get("conversation_id")
        payload = task.get("payload", {})
        
        # Publishing processing status with queue_position=0 (not in queue anymore, currently processing)
        await self.publish_status(job_id, "processing", 1, message_id, conv_id, prompt, queue_position=0, user_id=user_id, username=username)

        s = get_settings()
        checkpoint = getattr(s, "FORGE_FLUX_CHECKPOINT", "flux1-dev-bnb-nf4-v2.safetensors")
        forge_timeout = getattr(s, "FORGE_TIMEOUT", 180)

        # Flux Black Image Fix (Aligned with flux_stub.py):
        forge_payload = {
            "prompt": prompt,
            "steps": payload.get("steps", 20),
            "width": payload.get("width", 1024),
            "height": payload.get("height", 1024),
            "cfg_scale": 1.0,           # Standard Flux
            "sampler_name": "Euler",    # Proven sampler
            "scheduler": "Simple",      # Proven scheduler
            "distilled_cfg_scale": 3.5, # Critical for Flux
            "override_settings": {
                "sd_model_checkpoint": checkpoint,
            }
        }

        # Progress monitor start
        async def poll_with_user():
            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        async with session.get(self.progress_url, timeout=2) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                progress = int(data.get("progress", 0) * 100)
                                # Publishing progress with queue_position=0 (currently processing)
                                await self.publish_status(job_id, "processing", progress, message_id, conv_id, queue_position=0, user_id=user_id, username=username)
                                if progress >= 100: break
                    except Exception:
                        pass
                    await asyncio.sleep(1)

        monitor_task = asyncio.create_task(poll_with_user())

        try:
            logger.info(f"Starting generation for job: {job_id[:8]} (user: {user_id})")
            logger.info(f"Targeting Forge API: {self.forge_url} (Timeout: {forge_timeout}s)")
            
            try:
                async with httpx.AsyncClient(timeout=forge_timeout) as client:
                    resp = await client.post(self.forge_url, json=forge_payload)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.ConnectError:
                raise Exception(f"Forge API bağlantı hatası: {self.forge_url} adresine ulaşılamıyor. Forge servisinin --api parametresiyle açık olduğundan emin olun.")
            except httpx.TimeoutException:
                raise Exception(f"Forge API zaman aşımı: {forge_timeout} saniye içinde yanıt alınamadı.")
            except Exception as e:
                raise Exception(f"Forge API hatası: {str(e)}")
                
            if not monitor_task.done():
                monitor_task.cancel()
            
            images = data.get("images", [])
            if not images:
                logger.error(f"Forge response missing images keys: {list(data.keys())}")
                raise Exception("Forge API başarılı döndü ancak görsel üretilemedi (images listesi boş).")
            
            img_bytes = base64.b64decode(images[0].split(",")[-1])
            filename = f"atlas_{int(time.time())}_{job_id[:8]}.png"
            
            logger.info(f"Uploading file: {filename} to {self.upload_url}")
            files = {'file': (filename, img_bytes, 'image/png')}
            headers = {'x-forge-worker-token': self.worker_token}
            
            async with httpx.AsyncClient() as client:
                u_resp = await client.post(self.upload_url, files=files, headers=headers, timeout=60)
                u_resp.raise_for_status()
                u_data = u_resp.json()
                
            remote_url = u_data.get("image_url")
            # Publishing complete status with queue_position=0 (job completed, not in queue)
            await self.publish_status(job_id, "complete", 100, message_id, conv_id, image_url=remote_url, queue_position=0, user_id=user_id, username=username)
            logger.info(f"Job {job_id[:8]} completed: {remote_url}")
            
            # CRITICAL: Update message metadata for persistence (page reload)
            if message_id:
                try:
                    # Metadata to persist in DB
                    metadata_updates = {
                        "type": "image",
                        "status": "complete",
                        "image_url": remote_url,
                        "job_id": job_id,
                        "prompt": task.get("args", {}).get("prompt", "")
                    }
                    
                    # Run in thread pool (sync function in async context)
                    await asyncio.to_thread(update_message, message_id, None, metadata_updates)
                    logger.info(f"[PERSISTENCE] Message {message_id} metadata updated with image_url")
                except Exception as meta_err:
                    logger.error(f"[PERSISTENCE] Failed to update message metadata: {meta_err}")
                    # Don't fail the job, just log
            else:
                logger.warning(f"[PERSISTENCE] No message_id for job {job_id[:8]}, cannot persist image")

        except Exception as e:
            error_msg = str(e) or "Bilinmeyen bir hata oluştu"
            logger.error(f"Job {job_id[:8]} failed: {error_msg}")
            
            # Update DB to error state if possible
            if message_id:
                try:
                    metadata_updates = {
                        "type": "image",
                        "status": "error",
                        "error": error_msg,
                        "job_id": job_id,
                    }
                    await asyncio.to_thread(update_message, message_id, None, metadata_updates)
                except: pass

            # Publishing error status with queue_position=0 (job failed, not in queue)
            await self.publish_status(job_id, "error", 0, message_id, conv_id, error=error_msg, queue_position=0, user_id=user_id, username=username)
        finally:
            if not monitor_task.done():
                try: monitor_task.cancel()
                except: pass

    async def run_loop(self):
        await self.connect_redis()
        logger.info("Local Worker is now LISTENING for tasks...")
        
        # Start queue processor
        self.queue_processor_task = asyncio.create_task(self._queue_processor_loop())
        
        while self.is_running:
            try:
                if not self.redis_client:
                    await self.connect_redis()
                    
                try:
                    # Using LPOP on the client
                    data = await self.redis_client.lpop("atlas_image_tasks")
                except Exception as redis_err:
                    logger.error(f"Redis LPOP error: {redis_err}")
                    await asyncio.sleep(5)
                    # Reconnect attempt
                    self.redis_client = None
                    continue

                if data:
                    logger.info(f"Task popped! Length: {len(data)}")
                    task = json.loads(data)
                    logger.info(f"New task received: {task.get('job_id', 'unknown')[:8]}")
                    
                    # Increment total queued tasks counter and calculate queue position
                    self.total_queued_tasks += 1
                    queue_position = self.total_queued_tasks
                    
                    # Store queue position in task for later use
                    task['_queue_position'] = queue_position
                    
                    # Add to processing queue instead of direct processing
                    await self.processing_queue.put(task)
                    logger.info(f"Task queued for processing: {task.get('job_id', 'unknown')[:8]}, queue_pos={queue_position}")
                else:
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(5)
    
    async def _queue_processor_loop(self):
        """Sequential queue processor - ensures one job at a time"""
        logger.info("[QUEUE_PROCESSOR] Started - will process jobs sequentially")
        
        while self.is_running:
            try:
                # Get next task from queue
                task = await self.processing_queue.get()
                
                try:
                    job_id = task.get('job_id', 'unknown')[:8]
                    # Get queue position that was calculated when task entered queue
                    queue_pos = task.get('_queue_position', 1)
                    
                    logger.info(f"[QUEUE_PROCESSOR] Processing task: {job_id}, queue_pos={queue_pos}")
                    
                    # Publish queued status with position
                    try:
                        await self.publish_status(
                            task.get("job_id"),
                            "queued",
                            0,
                            task.get("message_id"),
                            task.get("conversation_id"),
                            task.get("prompt"),
                            queue_position=queue_pos,
                            user_id=task.get("user_id"),
                            username=task.get("username")
                        )
                        logger.info(f"[QUEUE_PROCESSOR] Published queued status: job={job_id}, queue_pos={queue_pos}")
                    except Exception as pub_err:
                        logger.error(f"[QUEUE_PROCESSOR] Failed to publish queued status: {pub_err}")
                    
                    # Acquire GPU lock - only one job processes at a time
                    async with self.gpu_lock:
                        logger.info(f"[GPU_LOCK] Acquired for job: {job_id}")
                        self.is_processing = True
                        
                        try:
                            # During processing, publish status with queue_position=0 (not in queue anymore)
                            await self.generate_and_upload(task)
                        finally:
                            self.is_processing = False
                            logger.info(f"[GPU_LOCK] Released for job: {job_id}")
                    
                    logger.info(f"[QUEUE_PROCESSOR] Task completed: {job_id}")
                    
                except Exception as e:
                    logger.error(f"[QUEUE_PROCESSOR] Task processing error: {e}", exc_info=True)
                    # Publish error status with queue_position=0 (not in queue)
                    try:
                        await self.publish_status(
                            task.get("job_id", "unknown"),
                            "error",
                            0,
                            task.get("message_id"),
                            task.get("conversation_id"),
                            task.get("prompt"),
                            error=str(e),
                            queue_position=0,
                            user_id=task.get("user_id"),
                            username=task.get("username")
                        )
                    except Exception as pub_err:
                        logger.error(f"[QUEUE_PROCESSOR] Failed to publish error status: {pub_err}")
                
                finally:
                    self.processing_queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info("[QUEUE_PROCESSOR] Cancelled")
                break
            except Exception as e:
                logger.error(f"[QUEUE_PROCESSOR] Loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

if __name__ == "__main__":
    worker = AtlasLocalWorker()
    try:
        asyncio.run(worker.run_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped.")
