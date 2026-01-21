"""
Budget tracker for LLM usage (request/token counters with simple thresholds).
Derived from standalone_router/Atlas/budget_tracker.py, simplified for shared use.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class AlertLevel(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


@dataclass
class ModelLimits:
    rpd: int  # requests per day
    tpd: int  # tokens per day


@dataclass
class UsageRecord:
    requests: int = 0
    tokens: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class BudgetAlert:
    model_id: str
    metric: str
    level: AlertLevel
    current: int
    limit: int
    percentage: float
    timestamp: datetime = field(default_factory=datetime.now)


class BudgetTracker:
    """Model/key level budget tracking with midnight reset."""

    DEFAULT_LIMITS: Dict[str, ModelLimits] = {
        "llama-3.1-8b-instant": ModelLimits(rpd=57600, tpd=5_000_000),
        "llama-3.3-70b-versatile": ModelLimits(rpd=4000, tpd=1_000_000),
        "llama-guard-3-8b": ModelLimits(rpd=57600, tpd=5_000_000),
        "llama-4-scout-17b-16e-instruct": ModelLimits(rpd=4000, tpd=1_000_000),
        "moonshotai/kimi-k2-instruct": ModelLimits(rpd=4000, tpd=1_000_000),
        "meta-llama/llama-4-maverick-17b-128e-instruct": ModelLimits(rpd=4000, tpd=1_000_000),
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
        if getattr(self, "_initialized", False):
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

    def set_custom_limits(self, model_id: str, rpd: int, tpd: int) -> None:
        self._custom_limits[model_id] = ModelLimits(rpd=rpd, tpd=tpd)

    def check_budget(self, model_id: str) -> Tuple[bool, Optional[str]]:
        self._check_and_reset()
        limits = self.get_limits(model_id)
        usage = self._usage.get(model_id, UsageRecord())
        if usage.requests >= limits.rpd:
            return False, f"Request budget exceeded for {model_id} ({usage.requests}/{limits.rpd})"
        if usage.tokens >= limits.tpd:
            return False, f"Token budget exceeded for {model_id} ({usage.tokens}/{limits.tpd})"
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
            self._key_usage[key_prefix].last_updated = datetime.now()

        return self._check_thresholds(model_id)

    def get_usage(self, model_id: str) -> UsageRecord:
        self._check_and_reset()
        return self._usage.get(model_id, UsageRecord())

    def _check_thresholds(self, model_id: str) -> List[BudgetAlert]:
        alerts: List[BudgetAlert] = []
        limits = self.get_limits(model_id)
        usage = self._usage.get(model_id, UsageRecord())

        req_pct = usage.requests / limits.rpd if limits.rpd else 0
        tok_pct = usage.tokens / limits.tpd if limits.tpd else 0

        for metric, pct, current, limit in [
            ("requests", req_pct, usage.requests, limits.rpd),
            ("tokens", tok_pct, usage.tokens, limits.tpd),
        ]:
            level = self._get_alert_level(pct)
            if level != AlertLevel.NORMAL:
                alert = BudgetAlert(
                    model_id=model_id,
                    metric=metric,
                    level=level,
                    current=current,
                    limit=limit,
                    percentage=round(pct * 100, 2),
                )
                if not self._alert_exists(alert):
                    alerts.append(alert)
                    self._alerts.append(alert)
        return alerts

    def _get_alert_level(self, pct: float) -> AlertLevel:
        if pct >= self.THRESHOLD_EXCEEDED:
            return AlertLevel.EXCEEDED
        if pct >= self.THRESHOLD_CRITICAL:
            return AlertLevel.CRITICAL
        if pct >= self.THRESHOLD_WARNING:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL

    def _alert_exists(self, alert: BudgetAlert) -> bool:
        return any(
            a.model_id == alert.model_id
            and a.metric == alert.metric
            and a.level == alert.level
            for a in self._alerts
        )

    def reset(self) -> None:
        """Test convenience reset."""
        self._usage.clear()
        self._key_usage.clear()
        self._alerts.clear()
        self._custom_limits.clear()
        self._last_reset_date = date.today()


budget_tracker = BudgetTracker()

