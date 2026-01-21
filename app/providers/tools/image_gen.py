import json
import uuid
import redis
import logging
import os
from typing import Any, Dict, Optional
from app.config import get_settings
from app.providers.tools.base import BaseTool
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger("app.provider.tools.image_gen")

class ImageGenTool(BaseTool):
    """
    Image Generation Tool.
    In Hybrid Architecture, this tool pushes tasks to a Redis Queue 
    to be processed by a Local Worker node.
    """
    
    def __init__(self):
        super().__init__(
            name="image_generator",
            description="Generates high-quality images from text prompts (Flux/SD)."
        )
        self.settings = get_settings()
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            try:
                # Use get_redis_url to support Upstash/URL configs correctly
                url = self.settings.get_redis_url(self.settings.REDIS_DB_QUEUE)
                self._redis = redis.from_url(
                    url,
                    decode_responses=True,
                    ssl_cert_reqs=None # For Upstash/Worker compatibility
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis Queue: {e}")
        return self._redis

    async def execute(self, prompt: str, user_id: str, username: str = None, message_id: int = None, conversation_id: str = None, priority: str = "normal", batch_id: str = None, timeout_seconds: int = 300, **kwargs) -> Dict[str, Any]:
        """
        Submits an image generation job to the queue.
        
        FAZE 4 Parameters:
        - priority: "low", "normal", or "high" (default: "normal")
        - batch_id: Optional batch identifier for atomic batch processing
        - timeout_seconds: Job timeout in seconds (default: 300 = 5 minutes)
        """
        job_id = str(uuid.uuid4())
        
        task = {
            "type": "image_gen",
            "job_id": job_id,
            "user_id": str(user_id),
            "username": username or str(user_id), # Critical for targeted WS delivery
            "message_id": message_id,
            "conversation_id": conversation_id,
            "prompt": prompt,
            "priority": priority,  # FAZE 4: Priority queue support
            "batch_id": batch_id,  # FAZE 4: Batch processing
            "timeout_seconds": timeout_seconds,  # FAZE 4: Timeout enforcement
            "payload": kwargs,
            "timestamp": uuid.uuid4().hex[:8]
        }

        try:
            # Emit Telemetry
            telemetry.emit(
                EventType.TOOL_EXECUTION,
                {"tool": self.name, "op": "submit_job", "job_id": job_id, "prompt": prompt[:50]},
                component="tool_image_gen"
            )

            # Push to Redis Queue (Upstash Hybrid)
            client = self._get_redis()
            if client:
                client.lpush("atlas_image_tasks", json.dumps(task))
                logger.info(f"[TOOL] Image job {job_id[:8]} pushed to Redis | message_id={message_id}")
                # E2E SMOKE LOG
                if self.settings.DEBUG and os.getenv("SMOKE_TEST_ENABLED", "false").lower() == "true":
                    logger.info(f"[E2E_SMOKE] QUEUED: job_id={job_id} message_id={message_id} conversation_id={conversation_id} status=queued")
                return {
                    "status": "queued",
                    "job_id": job_id,
                    "message_id": message_id,
                    "message": "Görsel üretim görevi yerel işleyiciye (worker) iletildi."
                }
            
            raise ConnectionError("Redis Queue (Upstash) bağlantısı kurulamadı.")

        except Exception as e:
            telemetry.emit(
                EventType.ERROR,
                {"tool": self.name, "error": str(e), "job_id": job_id},
                component="tool_image_gen"
            )
            logger.error(f"Image generation submission failed: {e}")
            return {"status": "error", "message": f"Kuyruğa ekleme hatası: {str(e)}"}

# Export instance
image_gen_tool = ImageGenTool()
