"""
LLM provider adapter registry.

Currently only Groq is wired; adapter signature aligns with LLMGenerator expectations.
"""
from __future__ import annotations

from typing import AsyncGenerator, Optional

from app.providers.llm.groq import GroqProvider
from app.core.llm.generator import LLMRequest


async def groq_adapter(
    model_id: str,
    api_key: str,
    request: LLMRequest,
    stream: bool = False,
) -> AsyncGenerator[str, None] | object:
    provider = GroqProvider(api_key=api_key)

    system_prompt = (request.metadata or {}).get("system_prompt")
    messages = request.messages or []
    base_prompt = request.prompt

    # Eğer prompt yoksa ve mesajlar zaten user içeriyorsa ekstra user ekleme
    prompt_for_call = base_prompt or ""
    append_user = bool(prompt_for_call)

    if stream:
        return provider.generate_stream(
            prompt=prompt_for_call,
            system_prompt=system_prompt,
            messages=messages if append_user else messages,
            model=model_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

    result_text = await provider.generate(
        prompt=prompt_for_call,
        system_prompt=system_prompt,
        messages=messages if append_user else messages,
        model=model_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )

    class Resp:
        def __init__(self, text: str, model: str):
            self.text = text
            self.model = model
            self.tokens = 0

    return Resp(result_text, model_id)


async def gemini_adapter(
    model_id: str,
    api_key: str,
    request: LLMRequest,
    stream: bool = False,
) -> AsyncGenerator[str, None] | object:
    from app.providers.llm.gemini import GeminiProvider
    provider = GeminiProvider(api_key=api_key)

    messages = request.messages or []
    prompt = request.prompt or ""
    metadata = request.metadata or {}
    system_prompt = metadata.get("system_prompt")
    temperature = request.temperature or 0.1

    if stream:
        async def _stream_wrapper():
            async for chunk in provider.generate_stream(
                prompt=prompt,
                messages=messages,
                model=model_id,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=request.max_tokens
            ):
                yield chunk
        return _stream_wrapper()

    response_text = await provider.generate(
        prompt=prompt,
        messages=messages,
        model=model_id,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=request.max_tokens
    )

    class Resp:
        def __init__(self, text: str, model: str):
            self.text = text
            self.model = model
            self.tokens = 0

    return Resp(response_text, model_id)
