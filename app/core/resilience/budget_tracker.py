"""
Mami AI - Bütçe ve Kullanım Takibi (Budget Tracker)
--------------------------------------------------
Model ve API anahtarı bazlı günlük kullanım miktarlarını takip eder.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, Optional, List, Tuple
from enum import Enum
import threading


class AlertLevel(Enum):
    """Uyarı seviyeleri."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


@dataclass
class ModelLimits:
    """Model için günlük limitler."""
    rpd: int  # Request Per Day
    tpd: int  # Token Per Day


@dataclass
class UsageRecord:
    """Kullanım verileri."""
    requests: int = 0
    tokens: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class BudgetAlert:
    """Bütçe uyarı objesi."""
    model_id: str
    metric: str
    level: AlertLevel
    current: int
    limit: int
    percentage: float
    timestamp: datetime = field(default_factory=datetime.now)


class BudgetTracker:
    """Model ve API anahtarı bazlı bütçe takip kontrolcüsü."""
    
    DEFAULT_LIMITS: Dict[str, ModelLimits] = {
        "llama-3.1-8b-instant": ModelLimits(rpd=57600, tpd=5_000_000),
        "llama-3.3-70b-versatile": ModelLimits(rpd=4000, tpd=1_000_000),
        "llama-guard-3-8b": ModelLimits(rpd=57600, tpd=5_000_000),
        "gemini-2.0-flash": ModelLimits(rpd=1500, tpd=1_000_000),
    }
    
    FALLBACK_LIMITS = ModelLimits(rpd=1000, tpd=500_000)
    
    THRESHOLD_WARNING = 0.80
    THRESHOLD_CRITICAL = 0.90
    THRESHOLD_EXCEEDED = 1.00
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._usage: Dict[str, UsageRecord] = {}
        self._key_usage: Dict[str, UsageRecord] = {}
        self._alerts: List[BudgetAlert] = []
        self._last_reset_date: date = date.today()
        self._custom_limits: Dict[str, ModelLimits] = {}
        self._initialized = True
    
    def _check_and_reset(self) -> None:
        today = date.today()
        if today > self._last_reset_date:
            self._usage.clear()
            self._key_usage.clear()
            self._alerts.clear()
            self._last_reset_date = today
    
    def get_limits(self, model_id: str) -> ModelLimits:
        if model_id in self._custom_limits:
            return self._custom_limits[model_id]
        return self.DEFAULT_LIMITS.get(model_id, self.FALLBACK_LIMITS)
    
    def check_budget(self, model_id: str) -> Tuple[bool, Optional[str]]:
        self._check_and_reset()
        limits = self.get_limits(model_id)
        usage = self._usage.get(model_id, UsageRecord())
        
        if usage.requests >= limits.rpd:
            return False, f"Günlük istek limiti aşıldı ({usage.requests}/{limits.rpd})"
        if usage.tokens >= limits.tpd:
            return False, f"Günlük token limiti aşıldı ({usage.tokens}/{limits.tpd})"
        return True, None
    
    def record_usage(self, model_id: str, tokens: int = 0, key_prefix: Optional[str] = None) -> List[BudgetAlert]:
        self._check_and_reset()
        
        if model_id not in self._usage:
            self._usage[model_id] = UsageRecord()
        
        self._usage[model_id].requests += 1
        self._usage[model_id].tokens += tokens
        self._usage[model_id].last_updated = datetime.now()
        
        if key_prefix:
            if key_prefix not in self._key_usage:
                self._key_usage[key_prefix] = UsageRecord()
            self._key_usage[key_prefix].requests += 1
            self._key_usage[key_prefix].tokens += tokens
        
        return self._check_thresholds(model_id)
    
    def _check_thresholds(self, model_id: str) -> List[BudgetAlert]:
        alerts = []
        limits = self.get_limits(model_id)
        usage = self._usage.get(model_id, UsageRecord())
        
        req_pct = usage.requests / limits.rpd if limits.rpd > 0 else 0
        req_level = self._get_alert_level(req_pct)
        
        if req_level != AlertLevel.NORMAL:
            alert = BudgetAlert(
                model_id=model_id, metric="requests", level=req_level,
                current=usage.requests, limit=limits.rpd, percentage=req_pct * 100
            )
            if not self._alert_exists(alert):
                alerts.append(alert)
                self._alerts.append(alert)
        
        return alerts
    
    def _get_alert_level(self, percentage: float) -> AlertLevel:
        if percentage >= self.THRESHOLD_EXCEEDED:
            return AlertLevel.EXCEEDED
        elif percentage >= self.THRESHOLD_CRITICAL:
            return AlertLevel.CRITICAL
        elif percentage >= self.THRESHOLD_WARNING:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL
    
    def _alert_exists(self, new_alert: BudgetAlert) -> bool:
        for alert in self._alerts:
            if (alert.model_id == new_alert.model_id and 
                alert.metric == new_alert.metric and 
                alert.level == new_alert.level):
                return True
        return False
    
    def get_usage_stats(self) -> Dict:
        self._check_and_reset()
        stats = {"date": self._last_reset_date.isoformat(), "models": {}, "alerts": []}
        
        for model_id, usage in self._usage.items():
            limits = self.get_limits(model_id)
            req_pct = (usage.requests / limits.rpd * 100) if limits.rpd > 0 else 0
            stats["models"][model_id] = {
                "requests": usage.requests,
                "limit": limits.rpd,
                "percentage": round(req_pct, 1)
            }
        
        return stats


# Singleton
budget_tracker = BudgetTracker()
