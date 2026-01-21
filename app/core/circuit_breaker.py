"""
Mami AI - Circuit Breaker Pattern
==================================

Circuit breaker pattern implementation for resilience.

Best Practices:
- Fail fast when service is down
- Automatic recovery testing
- Configurable thresholds
- Half-open state for testing recovery

Kullanım:
    from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    from redis.exceptions import ConnectionError

    redis_circuit_breaker = CircuitBreaker(
        "redis",
        CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout_seconds=60,
            expected_exception=ConnectionError
        )
    )

    result = await redis_circuit_breaker.call(get_redis)
"""

import asyncio
import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerConfig:
    """
    Circuit breaker configuration.

    Attributes:
        failure_threshold: Open circuit after N failures (default: 5)
        success_threshold: Close circuit after N successes in half-open (default: 2)
        timeout_seconds: Open circuit for N seconds (default: 60)
        expected_exception: Exception type to track (default: Exception)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception


class CircuitBreaker:
    """
    Circuit Breaker Pattern.

    Best Practices:
    - Fail fast when service is down
    - Automatic recovery testing
    - Configurable thresholds

    Attributes:
        name: Circuit breaker name (for logging)
        config: Circuit breaker configuration
        state: Current circuit state
        failure_count: Current failure count
        success_count: Current success count (in half-open state)
        last_failure_time: Timestamp of last failure

    Example:
        >>> redis_circuit_breaker = CircuitBreaker(
        ...     "redis",
        ...     CircuitBreakerConfig(
        ...         failure_threshold=5,
        ...         success_threshold=2,
        ...         timeout_seconds=60,
        ...         expected_exception=ConnectionError
        ...     )
        ... )
        >>>
        >>> result = await redis_circuit_breaker.call(get_redis)
    """

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute (can be async or sync)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            ExternalServiceError if circuit is OPEN
            Original exception if function fails
        """
        # Check if circuit should be opened/closed
        self._update_state()

        if self.state == CircuitState.OPEN:
            from app.core.exceptions import ExternalServiceError
            logger.warning(
                f"[CIRCUIT_BREAKER] {self.name} circuit is OPEN - rejecting request"
            )
            raise ExternalServiceError(
                service=self.name,
                message="Circuit breaker is OPEN - service unavailable",
                retryable=True,
                retry_after=self.config.timeout_seconds
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(
                    f"[CIRCUIT_BREAKER] {self.name} circuit CLOSED after {self.success_count} successes"
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            # Reset failure count on success in CLOSED state
            if self.failure_count > 0:
                logger.debug(
                    f"[CIRCUIT_BREAKER] {self.name} reset failure count after success"
                )
                self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.config.failure_threshold:
            logger.warning(
                f"[CIRCUIT_BREAKER] {self.name} circuit OPENED after {self.failure_count} failures"
            )
            self.state = CircuitState.OPEN

    def _update_state(self):
        """Update circuit breaker state."""
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    logger.info(
                        f"[CIRCUIT_BREAKER] {self.name} circuit entering HALF_OPEN state for recovery test"
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
