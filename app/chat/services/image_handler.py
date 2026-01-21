import asyncio
from typing import Any
from uuid import uuid4

from app.core.logger import get_logger
from app.image.image_manager import request_image_generation
from app.memory.conversation import append_message, update_message

logger = get_logger(__name__)


class ImageHandler:
    """Görsel üretim işlemlerini yöneten servis."""

    @staticmethod
    async def build_prompt(
        user_message: str, style_profile: dict[str, Any] | None = None, image_settings: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        """
        Tek prompt hattı: processor.build_image_prompt kullanılır.
        """
        from app.chat.processor import build_image_prompt

        return await build_image_prompt(user_message, style_profile=style_profile, image_settings=image_settings)

    @classmethod
    async def process_image_request(
        cls,
        username: str,
        message: str,
        conversation_id: str | None,
        user: Any,
        semantic: dict[str, Any],
        style_profile: dict[str, Any] | None = None,
        image_settings: dict[str, Any] | None = None,  # New param
    ) -> str:
        """
        Görsel isteğini işler:
        1. Prompt oluştur (Sync/Wait)
        2. Job ID oluştur
        3. Mesajı DB'ye kaydet (Pending)
        4. Job'u ASYNC başlat
        """
        from app.config import get_settings
        settings = get_settings()
        if settings.DEBUG:
            logger.debug(f"[IMAGE] ImageHandler.process_image_request CALLED: {username}, message_length={len(message)}")

        # 1. Prompt
        prompt, prompt_meta = await cls.build_prompt(message, style_profile, image_settings)

        # 2. Job ID
        job_id = str(uuid4())

        # 3. Mesaj (Pending)
        message_id = None
        if conversation_id:
            placeholder_msg = append_message(
                username=username,
                conv_id=conversation_id,
                role="bot",
                text="",  # doldurulacak
                extra_metadata={"type": "image", "status": "queued", "job_id": job_id, "prompt_hash": prompt_meta.get("prompt_hash"), "prompt_preview": prompt_meta.get("prompt_preview"), "prompt_length": prompt_meta.get("prompt_length")},
            )
            message_id = placeholder_msg.id
            # İçerik, frontend regex'iyle uyumlu olsun (numeric message_id)
            safe_message_id = message_id if message_id is not None else 0
            content = f"[IMAGE_QUEUED:{job_id}:{safe_message_id}] Görsel isteğiniz kuyruğa alındı..."
            update_message(message_id, content, {"type": "image", "status": "queued", "job_id": job_id, "prompt_hash": prompt_meta.get("prompt_hash"), "prompt_preview": prompt_meta.get("prompt_preview"), "prompt_length": prompt_meta.get("prompt_length")})
            logger.info(f"[IMAGE] Mesaj oluşturuldu (sync): {message_id}, job_id: {job_id[:8]}")

        # 4. Async Job Start
        async def _start_job():
            try:
                result_job_id = await request_image_generation(
                    username=username,
                    prompt=prompt,
                    message_id=message_id or 0,
                    job_id=job_id,
                    conversation_id=conversation_id,
                    user=user,
                    image_settings=image_settings,  # Pass to manager
                )
                if result_job_id:
                    logger.info(f"[IMAGE] Job başlatıldı: {result_job_id} -> mesaj: {message_id}")
            except Exception as e:
                logger.error(f"[IMAGE] Job başlatma hatası: {e}")
                if message_id:
                    update_message(message_id, f"❌ Görsel oluşturulamadı: {str(e)}", {"status": "error"})

        asyncio.create_task(_start_job())

        # Special return format for frontend handler
        # Ensure regex in frontend matches (numeric message_id or placeholder '0' if missing)
        safe_message_id = message_id if message_id is not None else "0"
        return f"[IMAGE_QUEUED:{job_id}:{safe_message_id}]"


# Global instance
image_handler = ImageHandler()









