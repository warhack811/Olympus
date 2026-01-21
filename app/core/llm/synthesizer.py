"""
Synthesizer fallback katmanı.

- governance.get_model_chain("synthesizer") zincirini dener
- generator benzeri ama sadece sentez rolü için sadeleştirilmiş
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, Dict, Optional

from app.core.llm.generator import LLMGenerator, LLMRequest, GeneratorResult
from app.core.llm.governance import governance

logger = logging.getLogger("app.core.llm.synthesizer")


class LLMSynthesizer:
    def __init__(self, generator: LLMGenerator) -> None:
        self.generator = generator

    async def synthesize(self, prompt: str, metadata: Optional[Dict] = None) -> GeneratorResult:
        request = LLMRequest(role="synthesizer", prompt=prompt, metadata=metadata)
        return await self.generator.generate(request)

    async def synthesize_stream(
        self, prompt: str, metadata: Optional[Dict] = None
    ) -> AsyncGenerator[str, None]:
        request = LLMRequest(role="synthesizer", prompt=prompt, metadata=metadata)
        async for chunk in self.generator.generate_stream(request):
            yield chunk

    def get_chain(self) -> list[str]:
        return governance.get_model_chain("synthesizer")

