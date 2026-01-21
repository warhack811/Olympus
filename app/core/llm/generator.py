"""
LLM generator abstraction.

Uses:
- governance: role -> model chain
- key_manager: provider aware key selection
- budget_tracker: per-model quota check

Adapters are injected per provider; no network calls here.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
import inspect
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional

from app.core.llm.budget_tracker import budget_tracker
from app.core.llm.governance import governance
from app.core.llm.key_manager import key_manager
from app.core.logger import get_logger

try:
    from app.core.telemetry.service import telemetry, EventType
except ImportError:
    telemetry = None
    EventType = None

logger = get_logger("app.core.llm.generator", use_json=False)


@dataclass
class LLMRequest:
    role: str
    prompt: Optional[str] = None
    messages: Optional[list] = None
    intent: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GeneratorResult:
    ok: bool
    text: str
    error_code: str = ""
    retryable: bool = False
    model: str = ""
    tokens: int = 0


Adapter = Callable[..., Awaitable[Any]]
StreamAdapter = Callable[..., AsyncGenerator[str, None]]


class LLMGenerator:
    def __init__(self, providers: Optional[Dict[str, Adapter]] = None) -> None:
        self.providers: Dict[str, Adapter] = providers or {}

    def register_provider(self, name: str, adapter: Adapter) -> None:
        self.providers[name] = adapter

    async def generate(self, request: LLMRequest, timeout: float = 30.0) -> GeneratorResult:
        """Generate with automatic fallback and timeout."""
        override_model = None
        if request.metadata:
            override_model = request.metadata.get("override_model")
        models = governance.with_override(request.role, override_model)
        errors: list[str] = []
        attempt_count = 0
        
        for model_id in models:
            attempt_count += 1
            provider_name = governance.detect_provider(model_id)
            adapter = self.providers.get(provider_name)
            
            # Log attempt with clear indicators
            is_fallback = attempt_count > 1
            fallback_marker = " [FALLBACK]" if is_fallback else ""
            logger.info(
                f"🚀 [LLMGenerator] {'🔄' if is_fallback else '🎯'} {request.role.upper()} katmanı için {model_id} deneniyor... "
                f"(Adım: {attempt_count}/{len(models)}){fallback_marker}"
            )
            
            if adapter is None:
                errors.append(f"{model_id}: provider '{provider_name}' not registered")
                logger.warning(f"[LLMGenerator] Provider not registered: {provider_name}")
                continue

            api_key = key_manager.get_best_key(model_id=model_id)
            if not api_key:
                errors.append(f"{model_id}: no api key available")
                logger.warning(f"[LLMGenerator] No API key for: {model_id}")
                continue

            budget_ok, budget_err = budget_tracker.check_budget(model_id)
            if not budget_ok:
                logger.warning(f"[LLMGenerator] Budget exceeded for: {model_id}")
                return GeneratorResult(
                    ok=False,
                    text=budget_err or "budget_exceeded",
                    error_code="BUDGET",
                    retryable=False,
                    model=model_id,
                )

            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    adapter(model_id=model_id, api_key=api_key, request=request),
                    timeout=timeout
                )
                text = getattr(result, "text", None) or str(result)
                tokens = getattr(result, "tokens", 0)
                
                # Success!
                budget_tracker.record_usage(model_id, tokens=tokens, key_prefix=api_key[:5])
                key_manager.report_success(api_key, model_id=model_id)
                
                logger.info(
                    f"✅ [LLMGenerator] BAŞARILI: {model_id} "
                    f"(Adım={attempt_count}, Fallback={'Evet' if attempt_count > 1 else 'Hayır'})"
                )
                
                # Telemetry
                if telemetry and EventType:
                    telemetry.emit(
                        EventType.LLM_GENERATION_SUCCESS,
                        {
                            "role": request.role,
                            "model": model_id,
                            "provider": provider_name,
                            "attempts": attempt_count,
                            "fallback": attempt_count > 1
                        },
                        component="llm_generator"
                    )
                
                return GeneratorResult(ok=True, text=text, model=model_id, tokens=tokens)
                
            except asyncio.TimeoutError:
                error_msg = f"{model_id}: timeout after {timeout}s"
                errors.append(error_msg)
                logger.warning(f"[LLMGenerator] TIMEOUT: {error_msg}")
                
                if telemetry and EventType:
                    telemetry.emit(
                        EventType.LLM_GENERATION_TIMEOUT,
                        {"role": request.role, "model": model_id, "timeout": timeout},
                        component="llm_generator"
                    )
                continue
                
            except Exception as exc:  # noqa: BLE001
                error_msg = f"{model_id}: {type(exc).__name__}: {exc}"
                errors.append(error_msg)
                key_manager.report_error(api_key, error_msg=str(exc), model_id=model_id)
                logger.error(f"[LLMGenerator] ERROR: {error_msg}")
                
                if telemetry and EventType:
                    telemetry.emit(
                        EventType.LLM_GENERATION_ERROR,
                        {
                            "role": request.role,
                            "model": model_id,
                            "error": str(exc),
                            "error_type": type(exc).__name__
                        },
                        component="llm_generator"
                    )
                continue

        # All models failed
        logger.error(
            f"[LLMGenerator] ALL FAILED for role={request.role}. "
            f"Models tried: {models}. Errors: {errors}"
        )
        
        if telemetry and EventType:
            telemetry.emit(
                EventType.LLM_GENERATION_ALL_FAILED,
                {
                    "role": request.role,
                    "models_tried": models,
                    "failed_count": len(models)
                },
                component="llm_generator"
            )
        
        return GeneratorResult(
            ok=False,
            text="; ".join(errors) if errors else "no_model_available",
            error_code="NO_MODEL",
            retryable=True,
            model=models[0] if models else "",
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        override_model = None
        if request.metadata:
            override_model = request.metadata.get("override_model")
        models = governance.with_override(request.role, override_model)
        errors: list[str] = []
        attempt_count = 0
        for model_id in models:
            attempt_count += 1
            provider_name = governance.detect_provider(model_id)
            adapter = self.providers.get(provider_name)
            
            is_fallback = attempt_count > 1
            fallback_marker = " [FALLBACK]" if is_fallback else ""
            logger.info(
                f"🚀 [LLMGenerator] {'🔄' if is_fallback else '🎯'} STREAM: {request.role.upper()} katmanı için {model_id} deneniyor... "
                f"(Adım: {attempt_count}/{len(models)}){fallback_marker}"
            )

            if adapter is None:
                errors.append(f"{model_id}: provider '{provider_name}' not registered")
                continue

            api_key = key_manager.get_best_key(model_id=model_id)
            if not api_key:
                errors.append(f"{model_id}: no api key available")
                continue

            budget_ok, budget_err = budget_tracker.check_budget(model_id)
            if not budget_ok:
                yield f"budget_exceeded:{budget_err}"
                return

            try:
                # Get the stream from adapter
                stream_or_awaitable = adapter(model_id=model_id, api_key=api_key, request=request, stream=True)
                
                if inspect.isawaitable(stream_or_awaitable):
                    stream = await stream_or_awaitable
                else:
                    stream = stream_or_awaitable
                
                # Iterate and yield from the generator
                async for chunk in stream:
                    yield chunk
                
                budget_tracker.record_usage(model_id, tokens=0, key_prefix=api_key[:5])
                key_manager.report_success(api_key, model_id=model_id)
                logger.info(f"✅ [LLMGenerator] STREAM BAŞARILI: {model_id}")
                return
            except Exception as exc:  # noqa: BLE001
                key_manager.report_error(api_key, error_msg=str(exc), model_id=model_id)
                errors.append(f"{model_id}: {exc}")
                continue

        if errors:
            yield f"error:{'; '.join(errors)}"
        else:
            yield "error:no_model_available"
