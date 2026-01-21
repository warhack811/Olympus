"""
Mami AI - Devre Kesici (Circuit Breaker)
----------------------------------------
Dış servislerde ardışık hataları takip eder ve sistemi korumak için akışı keser.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict


class CircuitState(Enum):
    """Devre kesicinin alabileceği durum değerleri."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitStats:
    """Hata ve başarı istatistikleri."""
    fail_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    state: CircuitState = CircuitState.CLOSED


class CircuitBreaker:
    """Dış servis çağrılarını denetleyen ve hata durumunda devreyi kesen sınıf."""
    
    def __init__(self, service_name: str, fail_threshold: int = 5, reset_timeout: int = 60):
        self.service_name = service_name
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.stats = CircuitStats()
    
    def can_execute(self) -> bool:
        """İstek yapılabilir mi?"""
        if self.stats.state == CircuitState.CLOSED:
            return True
        
        if self.stats.state == CircuitState.OPEN:
            if time.time() - self.stats.last_state_change > self.reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
        
        if self.stats.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Başarılı çağrı kaydı."""
        self.stats.total_calls += 1
        self.stats.success_count += 1
        
        if self.stats.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.CLOSED)
            self.stats.fail_count = 0
    
    def record_failure(self):
        """Hatalı çağrı kaydı."""
        self.stats.total_calls += 1
        self.stats.fail_count += 1
        self.stats.last_failure_time = time.time()
        
        if self.stats.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self.stats.state == CircuitState.CLOSED:
            if self.stats.fail_count >= self.fail_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def _transition_to(self, new_state: CircuitState):
        """Durum değişikliği."""
        import logging
        logging.getLogger(__name__).info(
            f"[CircuitBreaker] {self.service_name}: {self.stats.state.value} -> {new_state.value}"
        )
        self.stats.state = new_state
        self.stats.last_state_change = time.time()
    
    def get_status(self) -> dict:
        """Güncel durum özeti."""
        return {
            "service": self.service_name,
            "state": self.stats.state.value,
            "fail_count": self.stats.fail_count,
            "success_count": self.stats.success_count,
            "is_open": self.stats.state == CircuitState.OPEN
        }


class CircuitManager:
    """Tüm servis şalterlerini merkezi yöneten sınıf."""
    _circuits: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get_breaker(cls, service_name: str) -> CircuitBreaker:
        if service_name not in cls._circuits:
            cls._circuits[service_name] = CircuitBreaker(service_name)
        return cls._circuits[service_name]
    
    @classmethod
    def get_all_status(cls) -> list:
        return [cb.get_status() for cb in cls._circuits.values()]
