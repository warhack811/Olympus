import time
import logging
from typing import Any, Dict, Optional
from groq import AsyncGroq
from app.config import get_settings
from app.providers.llm.base import BaseLLMProvider
from app.core.telemetry.service import telemetry, EventType

logger = logging.getLogger("app.provider.llm.groq")

class GroqProvider(BaseLLMProvider):
    """
    Groq Cloud Provider implementation.
    Optimized for high-speed inference.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None
        # Varsayılan model governance'dan alınır
        from app.core.llm.governance import governance
        chain = governance.get_model_chain("synthesizer")
        self.default_model = chain[0] if chain else "llama-3.3-70b-versatile"

    async def generate(
        self, 
        prompt: Optional[str] = None, 
        system_prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs
    ) -> str:
        if not self.client:
            raise ValueError("Groq API Key is not configured.")

        model_name = kwargs.get("model", self.default_model)
        start_time = time.time()
        
        # Prepare messages
        llm_messages = []
        if system_prompt:
            llm_messages.append({"role": "system", "content": system_prompt})
        
        if messages:
            for msg in messages:
                llm_messages.append({"role": msg["role"], "content": msg["content"]})
        
        if prompt is not None:
            llm_messages.append({"role": "user", "content": prompt})

        try:
            telemetry.emit(
                EventType.LLM_REQUEST,
                {"provider": "groq", "model": model_name, "op": "request_in"},
                component="llm_groq"
            )

            # Cap max_tokens for guard models to avoid context window errors
            max_tokens = kwargs.get("max_tokens", 8192)
            if "guard" in model_name:
                max_tokens = min(max_tokens, 1024)
            
            completion = await self.client.chat.completions.create(
                model=model_name,
                messages=llm_messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=max_tokens
            )

            result_text = completion.choices[0].message.content
            duration = time.time() - start_time

            # Token usage recording if available
            usage = completion.usage
            telemetry.emit(
                EventType.LLM_REQUEST,
                {
                    "provider": "groq", 
                    "model": model_name, 
                    "duration": duration,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens
                },
                component="llm_groq"
            )

            return result_text

        except Exception as e:
            duration = time.time() - start_time
            telemetry.emit(
                EventType.ERROR,
                {"provider": "groq", "error": str(e), "duration": duration},
                component="llm_groq"
            )
            logger.error(f"Groq generation failed: {e}")
            raise

    async def generate_stream(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs
    ):
        if not self.client:
            raise ValueError("Groq API Key is not configured.")

        model_name = kwargs.get("model", self.default_model)
        
        llm_messages = []
        if system_prompt:
            llm_messages.append({"role": "system", "content": system_prompt})
        if messages:
            for msg in messages:
                llm_messages.append({"role": msg["role"], "content": msg["content"]})
        if prompt is not None:
            llm_messages.append({"role": "user", "content": prompt})

        try:
            # Cap max_tokens for guard models
            max_tokens = kwargs.get("max_tokens", 8192)
            if "guard" in model_name:
                max_tokens = min(max_tokens, 1024)

            stream = await self.client.chat.completions.create(
                model=model_name,
                messages=llm_messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Groq streaming failed: {e}")
            raise


# REDUNDANT WRAPPERS REMOVED
# Use app.core.llm.adapters.groq_adapter for centralized LLM calls



