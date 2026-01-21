"""
Mami AI - API Anahtarı Yöneticisi (Atlas Sovereign Edition)
-----------------------------------------------------------
Çoklu sağlayıcıdan (Groq, Gemini) gelen API anahtarlarının rotasyonu ve sağlık takibi.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum

from app.config import get_settings


class KeyStatus(Enum):
    """API anahtarının güncel durumu."""
    HEALTHY = "healthy"
    COOLDOWN = "cooldown"
    EXHAUSTED = "exhausted"
    DISABLED = "disabled"


@dataclass
class KeyStats:
    """Bir API anahtarına ait performans ve kullanım istatistikleri."""
    key_id: str
    key_masked: str
    status: KeyStatus = KeyStatus.HEALTHY
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    
    model_usage: dict = field(default_factory=dict)
    
    last_used: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    last_error: Optional[str] = None
    model_exhausted: dict = field(default_factory=dict)
    
    daily_requests: int = 0
    daily_reset_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    # Actual key stored privately
    _actual_key: str = ""
    
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
    
    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "key_masked": self.key_masked,
            "status": self.status.value,
            "success_rate": round(self.success_rate, 2),
            "total_requests": self.total_requests,
            "daily_requests": self.daily_requests,
            "rate_limit_hits": self.rate_limit_hits,
        }


class KeyManager:
    """Kurumsal API Anahtarı Yöneticisi - Çoklu sağlayıcı rotasyonu."""
    
    _pools: Dict[str, Dict[str, KeyStats]] = {"groq": {}, "gemini": {}}
    _cooldown_seconds: int = 60
    _initialized: bool = False
    
    @classmethod
    def initialize(cls, groq_keys: list = None, gemini_keys: list = None) -> None:
        if groq_keys:
            cls._pools["groq"] = {}
            for i, key in enumerate(groq_keys):
                if not key: continue
                key_id = f"groq_{i+1}"
                stats = KeyStats(key_id=key_id, key_masked=f"...{key[-4:]}" if len(key) > 4 else "****")
                stats._actual_key = key
                cls._pools["groq"][key_id] = stats
        
        if gemini_keys:
            cls._pools["gemini"] = {}
            for i, key in enumerate(gemini_keys):
                if not key: continue
                key_id = f"gemini_{i+1}"
                stats = KeyStats(key_id=key_id, key_masked=f"...{key[-4:]}" if len(key) > 4 else "****")
                stats._actual_key = key
                cls._pools["gemini"][key_id] = stats
        
        cls._initialized = True
    
    @classmethod
    def get_best_key(cls, model_id: Optional[str] = None) -> Optional[str]:
        if not cls._initialized:
            cls._auto_initialize()
        
        provider = cls._detect_provider(model_id)
        if provider not in cls._pools:
            return None
        
        cls._check_daily_reset()
        
        available = [s for s in cls._pools[provider].values() if s.is_available(model_id)]
        if not available:
            return None
        
        best = sorted(available, key=lambda k: (k.daily_requests, -k.success_rate))[0]
        return best._actual_key
    
    @classmethod
    def report_success(cls, api_key: str, model_id: str = None) -> None:
        stats = cls._find_by_key(api_key)
        if stats:
            stats.total_requests += 1
            stats.successful_requests += 1
            stats.daily_requests += 1
            stats.last_used = datetime.now()
            if model_id:
                stats.model_usage[model_id] = stats.model_usage.get(model_id, 0) + 1
    
    @classmethod
    def report_error(cls, api_key: str, status_code: int = 0, error_msg: str = "", model_id: str = None) -> None:
        stats = cls._find_by_key(api_key)
        if not stats: return
        
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.daily_requests += 1
        stats.last_used = datetime.now()
        stats.last_error = error_msg or f"HTTP {status_code}"
        
        error_lower = error_msg.lower()
        if any(x in error_lower for x in ["quota", "exhausted", "limit exceeded"]) and model_id:
            now = datetime.now()
            stats.model_exhausted[model_id] = datetime(now.year, now.month, now.day) + timedelta(days=1)
            return
        
        if status_code == 503:
            return
        
        if status_code == 429:
            stats.rate_limit_hits += 1
            stats.status = KeyStatus.COOLDOWN
            stats.cooldown_until = datetime.now() + timedelta(seconds=cls._cooldown_seconds)
    
    @classmethod
    def get_stats(cls) -> list:
        if not cls._initialized: cls._auto_initialize()
        return [s.to_dict() for pool in cls._pools.values() for s in pool.values()]
    
    @classmethod
    def _detect_provider(cls, model_id: str) -> str:
        if not model_id: return "groq"
        mid = model_id.lower()
        if any(x in mid for x in ["gemini", "google"]):
            return "gemini"
        return "groq"
    
    @classmethod
    def _find_by_key(cls, api_key: str) -> Optional[KeyStats]:
        for pool in cls._pools.values():
            for stats in pool.values():
                if stats._actual_key == api_key:
                    return stats
        return None
    
    @classmethod
    def _check_daily_reset(cls) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        for pool in cls._pools.values():
            for stats in pool.values():
                if stats.daily_reset_date != today:
                    stats.daily_requests = 0
                    stats.daily_reset_date = today
                    stats.model_exhausted = {}
    
    @classmethod
    def _auto_initialize(cls) -> None:
        settings = get_settings()
        cls.initialize(
            groq_keys=settings.get_groq_api_keys(),
            gemini_keys=settings.get_gemini_api_keys()
        )


# Singleton
key_manager = KeyManager()
