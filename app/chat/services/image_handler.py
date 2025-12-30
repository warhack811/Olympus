import asyncio
from typing import Any
from uuid import uuid4

from app.ai.prompts.image_guard import sanitize_image_prompt
from app.chat.decider import call_groq_api_safe_async
from app.core.logger import get_logger
from app.image.image_manager import request_image_generation
from app.memory.conversation import append_message, update_message

logger = get_logger(__name__)


class ImageHandler:
    """Görsel üretim işlemlerini yöneten servis."""

    @staticmethod
    async def build_prompt(
        user_message: str, style_profile: dict[str, Any] | None = None, image_settings: dict[str, Any] | None = None
    ) -> str:
        """
        Gorsel uretimi icin prompt olusturur.
        Prefix Kurallari: '!' ile basliyorsa raw prompt, yoksa translate/expand.
        """
        logger.warning(
            f"[DEBUG_EXCLAIM] Gelen mesaj: '{user_message}' | starts with !: {user_message.strip().startswith('!')}"
        )

        normalized = user_message.strip()

        # 1. RAW PROMPT (Prefix !)
        if normalized.startswith("!"):
            prompt = normalized.lstrip("!").strip() or normalized.lstrip("!")
            logger.info(f"[IMAGE_PROMPT] raw_prompt=True | '{user_message}' -> '{prompt}'")
            return prompt

        # 2. TRANSLATION (Groq) - Style-aware
        # Determine target style for LLM guidance
        target_style = ""
        style_descriptions = {
            "realistic": "photorealistic, cinematic, raw photo style",
            "anime": "anime/manga style, vibrant colors, cel shading",
            "artistic": "digital art, concept art style",
            "3d": "3D rendered, volumetric lighting",
            "sketch": "pencil sketch, hand drawn, line art",
            "pixel": "pixel art, retro 16-bit game style",
        }
        if image_settings:
            selected_style = image_settings.get("defaultStyle", "")
            if selected_style in style_descriptions:
                target_style = style_descriptions[selected_style]

        # Build system prompt with optional style guidance
        style_instruction = ""
        if target_style:
            style_instruction = (
                f"Target visual style: {target_style}. Describe the scene in a way that fits this style. "
            )

        detail_messages = [
            {
                "role": "system",
                "content": (
                    "You are an image prompt translator. "
                    "Translate and expand the user's request into a visual English prompt for Flux. "
                    f"{style_instruction}"
                    "Describe the scene visually in 1-2 sentences. "
                    "CRITICAL: Output MUST be in English, regardless of the input language. "
                    "Output ONLY the prompt text, no explanations or prefixes."
                ),
            },
            {"role": "user", "content": user_message},
        ]
        detailed, _ = await call_groq_api_safe_async(detail_messages, temperature=0.4)
        prompt = detailed.strip() if detailed else user_message.strip()

        # 3. GUARD (Forbidden Token)
        prompt = sanitize_image_prompt(prompt, user_message)

        # 4. STYLE INJECTION
        if style_profile:
            extras = []

            # Detail Level
            if style_profile.get("detail_level") == "long":
                detail_keywords = ["detay", "detail", "ayrıntı", "ayrinti"]
                if any(kw in user_message.lower() for kw in detail_keywords):
                    extras.extend(["highly detailed", "intricate details"])

            if extras:
                unique_extras = list(dict.fromkeys(extras))
                prompt = f"{prompt}, {', '.join(unique_extras)}"

        # 5. IMAGE SETTINGS STYLE INJECTION (from frontend imageSettings.defaultStyle)
        if image_settings:
            style_extras = []

            # Map frontend style values to prompt keywords
            style_map = {
                "realistic": ["photorealistic", "8k", "raw photo", "cinematic lighting"],
                "anime": ["anime style", "vibrant colors", "cel shading"],
                "artistic": ["digital art", "concept art", "trending on artstation"],
                "3d": ["3d render", "unreal engine 5", "octane render", "volumetric lighting"],
                "sketch": ["pencil sketch", "hand drawn", "line art", "black and white"],
                "pixel": ["pixel art", "16-bit", "retro game style", "pixelated"],
            }

            default_style = image_settings.get("defaultStyle", "")
            if default_style in style_map:
                style_extras.extend(style_map[default_style])
                logger.info(f"[IMAGE_STYLE] Applied style '{default_style}': {style_map[default_style]}")

            if style_extras:
                prompt = f"{prompt}, {', '.join(style_extras)}"

        logger.info(f"[IMAGE_PROMPT] raw_prompt=False | '{user_message}' -> '{prompt}'")
        return prompt

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
        print(f"[DEBUG_PRINT] ImageHandler.process_image_request CALLED: {username}, {message[:30]}...")

        # 1. Prompt
        prompt = await cls.build_prompt(message, style_profile, image_settings)

        # 2. Job ID
        job_id = str(uuid4())

        # 3. Mesaj (Pending)
        message_id = None
        if conversation_id:
            placeholder_msg = append_message(
                username=username,
                conv_id=conversation_id,
                role="bot",
                text="[IMAGE_PENDING] Görsel isteğiniz kuyruğa alındı...",
                extra_metadata={"type": "image", "status": "queued", "job_id": job_id, "prompt": prompt[:200]},
            )
            message_id = placeholder_msg.id
            logger.info(f"[IMAGE] Mesaj oluşturuldu (sync): {message_id}, job_id: {job_id[:8]}")

        # 4. Async Job Start
        async def _start_job():
            try:
                result_job_id = request_image_generation(
                    username=username,
                    prompt=prompt,
                    message_id=message_id,
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
        return f"[IMAGE_QUEUED:{job_id}:{message_id}]"


# Global instance
image_handler = ImageHandler()
