"""
LLM key manager (Groq/Gemini focused).

- Pool based key tracking
- Cooldown (429) and quota markers
- Provider detection by model name
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger("app.core.llm.key_manager", use_json=False)


class KeyStatus(Enum):
    HEALTHY = "healthy"
    COOLDOWN = "cooldown"
    EXHAUSTED = "exhausted"
    DISABLED = "disabled"


@dataclass
class KeyStats:
    key_id: str
    key_masked: str
    status: KeyStatus = KeyStatus.HEALTHY
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    last_used: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    last_error: Optional[str] = None
    model_usage: Dict[str, int] = field(default_factory=dict)
    model_exhausted: Dict[str, datetime] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    def is_available(self, model_id: Optional[str] = None) -> bool:
        if self.status == KeyStatus.DISABLED:
            return False

        if model_id and model_id in self.model_exhausted:
            if datetime.now() < self.model_exhausted[model_id]:
                return False
            del self.model_exhausted[model_id]

        if self.status == KeyStatus.COOLDOWN:
            if self.cooldown_until and datetime.now() < self.cooldown_until:
                return False
            self.status = KeyStatus.HEALTHY
        return True

    def mark_cooldown(self, seconds: int) -> None:
        self.status = KeyStatus.COOLDOWN
        self.cooldown_until = datetime.now() + timedelta(seconds=seconds)

    def mark_exhausted_until_midnight(self, model_id: str) -> None:
        tomorrow = (
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        self.model_exhausted[model_id] = tomorrow


class LLMKeyManager:
    _pools: Dict[str, Dict[str, KeyStats]] = {"groq": {}, "gemini": {}}
    _cooldown_seconds: int = 60
    _initialized: bool = False

    @classmethod
    def initialize(
        cls, groq_keys: Optional[list[str]] = None, gemini_keys: Optional[list[str]] = None
    ) -> None:
        cls._pools = {"groq": {}, "gemini": {}}
        if groq_keys:
            for i, key in enumerate(groq_keys):
                if not key:
                    continue
                key_id = f"groq_{i+1}"
                stats = KeyStats(key_id=key_id, key_masked=_mask(key))
                stats._actual_key = key
                cls._pools["groq"][key_id] = stats
        if gemini_keys:
            for i, key in enumerate(gemini_keys):
                if not key:
                    continue
                key_id = f"gemini_{i+1}"
                stats = KeyStats(key_id=key_id, key_masked=_mask(key))
                stats._actual_key = key
                cls._pools["gemini"][key_id] = stats
        cls._initialized = True

    @classmethod
    def _auto_initialize(cls) -> None:
        if cls._initialized:
            return
        settings = get_settings()
        groq_keys = settings.get_groq_api_keys()
        gemini_keys = settings.get_gemini_api_keys()
        
        # DEBUG: Print masked keys to see what's actually loaded
        masked_groq = [f"{k[:6]}...{k[-4:]}" if len(k) > 10 else "SHORT/EMPTY" for k in groq_keys]
        masked_gemini = [f"{k[:6]}...{k[-4:]}" if len(k) > 10 else "SHORT/EMPTY" for k in gemini_keys]
        
        logger.info(f"[KeyManager] Initializing. Groq: {masked_groq}, Gemini: {masked_gemini}")
        
        if not gemini_keys:
            logger.warning("[KeyManager] CRITICAL: settings.get_gemini_api_keys() returned EMPTY LIST")
            
        cls.initialize(groq_keys, gemini_keys)

    @classmethod
    def _detect_provider(cls, model_id: Optional[str]) -> str:
        if not model_id:
            return "groq"
        mid = model_id.lower()
        if any(x in mid for x in ("gemini", "google")):
            return "gemini"
        return "groq"

    @classmethod
    def get_best_key(cls, model_id: Optional[str] = None) -> Optional[str]:
        cls._auto_initialize()
        provider = cls._detect_provider(model_id)
        pool = cls._pools.get(provider, {})
        
        # [ROBUSTNESS FIX] If pool is empty, try ONE more re-init
        if not pool and provider in ("groq", "gemini"):
            logger.info(f"[KeyManager] Pool for '{provider}' is empty for model '{model_id}', attempting forced re-init from settings...")
            settings = get_settings()
            cls.initialize(settings.get_groq_api_keys(), settings.get_gemini_api_keys())
            pool = cls._pools.get(provider, {})

        available = [s for s in pool.values() if s.is_available(model_id)]
        if not available:
            return None
        best = sorted(available, key=lambda s: (s.total_requests, -s.success_rate))[0]
        return getattr(best, "_actual_key", None)

    @classmethod
    def report_success(cls, api_key: str, model_id: Optional[str] = None) -> None:
        stats = cls._find(api_key)
        if not stats:
            return
        stats.total_requests += 1
        stats.successful_requests += 1
        stats.last_used = datetime.now()
        if model_id:
            stats.model_usage[model_id] = stats.model_usage.get(model_id, 0) + 1
        
        logger.info(f"✅ [KeyManager] Success! Key: {stats.key_masked}, Model: {model_id}")

    @classmethod
    def report_error(
        cls,
        api_key: str,
        status_code: int | None = None,
        error_msg: str = "",
        model_id: Optional[str] = None,
    ) -> None:
        stats = cls._find(api_key)
        if not stats:
            return
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.last_used = datetime.now()
        stats.last_error = error_msg or (f"HTTP {status_code}" if status_code else "")

        err_lower = (error_msg or "").lower()
        logger.warning(f"❌ [KeyManager] Error with Key: {stats.key_masked}, Model: {model_id}, Error: {error_msg}")
        
        if status_code == 429:
            stats.rate_limit_hits += 1
            stats.mark_cooldown(cls._cooldown_seconds)
            logger.warning(f"⏳ [KeyManager] Key {stats.key_masked} entered COOLDOWN for {cls._cooldown_seconds}s (Rate Limit: 429)")
            return
        if status_code and status_code >= 500:
            stats.mark_cooldown(cls._cooldown_seconds)
            return
        if any(x in err_lower for x in ("quota", "exceeded")) and model_id:
            stats.mark_exhausted_until_midnight(model_id)
            logger.warning(f"🚫 [KeyManager] Key {stats.key_masked} EXHAUSTED for model {model_id} until midnight")

    @classmethod
    def get_stats(cls) -> list[dict]:
        cls._auto_initialize()
        res: list[dict] = []
        for pool in cls._pools.values():
            res.extend(
                [
                    {
                        "id": s.key_id,
                        "masked": s.key_masked,
                        "status": s.status.value,
                        "success_rate": round(s.success_rate, 2),
                        "total_requests": s.total_requests,
                        "failed_requests": s.failed_requests,
                        "rate_limit_hits": s.rate_limit_hits,
                    }
                    for s in pool.values()
                ]
            )
        return res

    @classmethod
    def reset(cls) -> None:
        """Test convenience reset."""
        cls._pools = {"groq": {}, "gemini": {}}
        cls._initialized = False

    @classmethod
    def _find(cls, api_key: str) -> Optional[KeyStats]:
        for pool in cls._pools.values():
            for stats in pool.values():
                if getattr(stats, "_actual_key", None) == api_key:
                    return stats
        return None


def _mask(key: str) -> str:
    return f"...{key[-4:]}" if len(key) > 4 else "****"


# Singleton alias for convenience
key_manager = LLMKeyManager

