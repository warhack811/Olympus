import time
import logging
import asyncio
import random
from typing import Any, Dict, Optional, AsyncGenerator
from google import genai
from google.genai import types  # For error types
from app.config import get_settings
from app.providers.llm.base import BaseLLMProvider
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger("app.provider.llm.gemini")

class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini Provider implementation.
    Refactored to play nice with ModelGovernance and LLMGenerator fallbacks.
    Internal retries removed; 429 errors are now handled by KeyManager/LLMGenerator.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.default_model = "gemini-2.0-flash"

    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs
    ) -> str:
        """
        Generates content with Gemini. Supports Vision (images).
        """
        if not self.client:
            raise ValueError("Gemini API Client is not initialized. Check API Key.")

        model_name = kwargs.get("model", self.default_model)
        start_time = time.time()
        
        # Merge model-specific vision capabilities if needed (flash models are great for vision)
        if "flash" not in model_name and "pro" not in model_name:
            model_name = self.default_model

        # Prepare contents
        contents = []
        if messages:
            for msg in messages:
                parts = []
                if "content" in msg:
                    parts.append({"text": msg["content"]})
                
                # Check for images in message
                if "images" in msg and msg["images"]:
                    for img_data in msg["images"]:
                        # If base64 format (data:image/...) or path needs to be read
                        if isinstance(img_data, str) and img_data.startswith("data:"):
                            mime, b64_data = img_data.split(";base64,")
                            mime = mime.replace("data:", "")
                            parts.append({"inline_data": {"mime_type": mime, "data": b64_data}})
                        elif isinstance(img_data, str):
                            # Assume it's a relative path from UPLOAD_ROOT
                            try:
                                from pathlib import Path
                                img_path = Path("data") / "uploads" / img_data
                                if img_path.exists():
                                    import base64
                                    import mimetypes
                                    with open(img_path, "rb") as f:
                                        b64 = base64.b64encode(f.read()).decode("utf-8")
                                        mime = mimetypes.guess_type(img_path)[0] or "image/jpeg"
                                        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
                            except Exception as e:
                                logger.warning(f"[Gemini] Failed to load image from path {img_data}: {e}")
                
                contents.append({"role": "user" if msg["role"] == "user" else "model", "parts": parts})
        
        if prompt:
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        try:
            # Emit Request Telemetry
            if telemetry:
                telemetry.emit(
                    EventType.LLM_REQUEST,
                    {"provider": "gemini", "model": model_name, "op": "request_in", "has_images": "images" in locals()},
                    component="llm_gemini"
                )

            # TRUE ASYNC: Use client.aio for non-blocking API calls
            response = await self.client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config={
                    "system_instruction": system_prompt,
                    "temperature": kwargs.get("temperature", 0.1),
                    "max_output_tokens": kwargs.get("max_tokens")
                }
            )

            duration = time.time() - start_time
            result_text = response.text

            # Emit Success Telemetry
            if telemetry:
                telemetry.emit(
                    EventType.LLM_REQUEST,
                    {
                        "provider": "gemini", 
                        "model": model_name, 
                        "duration": duration,
                        "response_length": len(result_text or "")
                    },
                    component="llm_gemini"
                )

            return result_text

        except Exception as e:
            duration = time.time() - start_time
            if telemetry:
                telemetry.emit(
                    EventType.ERROR,
                    {"provider": "gemini", "model": model_name, "error": str(e), "duration": duration},
                    component="llm_gemini"
                )
            logger.error(f"[Gemini] Error with model {model_name}: {e}")
            raise e

    async def generate_stream(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Streams content with Gemini. Supports Vision.
        """
        if not self.client:
            raise ValueError("Gemini API Client is not initialized.")

        model_name = kwargs.get("model", self.default_model)
        
        contents = []
        if messages:
            for msg in messages:
                parts = []
                if "content" in msg:
                    parts.append({"text": msg["content"]})
                
                if "images" in msg and msg["images"]:
                    for img_data in msg["images"]:
                        if isinstance(img_data, str) and img_data.startswith("data:"):
                            mime, b64_data = img_data.split(";base64,")
                            mime = mime.replace("data:", "")
                            parts.append({"inline_data": {"mime_type": mime, "data": b64_data}})
                        elif isinstance(img_data, str):
                            try:
                                from pathlib import Path
                                img_path = Path("data") / "uploads" / img_data
                                if img_path.exists():
                                    import base64
                                    import mimetypes
                                    with open(img_path, "rb") as f:
                                        b64 = base64.b64encode(f.read()).decode("utf-8")
                                        mime = mimetypes.guess_type(img_path)[0] or "image/jpeg"
                                        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
                            except Exception as e:
                                logger.warning(f"[Gemini] Failed to load image from path {img_data}: {e}")
                
                contents.append({"role": "user" if msg["role"] == "user" else "model", "parts": parts})
        
        if prompt:
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        try:
            async for chunk in self.client.aio.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config={
                    "system_instruction": system_prompt,
                    "temperature": kwargs.get("temperature", 0.1),
                    "max_output_tokens": kwargs.get("max_tokens")
                }
            ):
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"[Gemini] Streaming failed: {e}")
            raise e


# REDUNDANT ADAPTER REMOVED
# Use app.core.llm.adapters.gemini_adapter for centralized LLM calls
