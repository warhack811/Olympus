"""
Mami AI - Retry Utility
========================

Retry mekanizması için utility fonksiyonları.

Best Practices:
- Exponential backoff
- Maximum delay cap
- Retryable exception filtering
- Async/sync function support

Kullanım:
    from app.core.retry import retry_with_backoff, RetryConfig
    from redis.exceptions import ConnectionError, TimeoutError

    result = await retry_with_backoff(
        redis_client.get,
        RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            retryable_exceptions=(ConnectionError, TimeoutError)
        ),
        key
    )
"""

import asyncio
import logging
from typing import Callable, TypeVar, Tuple, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """
    Retry configuration.

    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        exponential_base: Exponential backoff base (default: 2.0)
        retryable_exceptions: Tuple of exception types to retry (default: (Exception,))
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: Tuple[type[Exception], ...] = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


async def retry_with_backoff(
    func: Callable[..., T],
    config: RetryConfig = RetryConfig(),
    *args,
    **kwargs
) -> T:
    """
    Retry function with exponential backoff.

    Best Practices:
    - Exponential backoff
    - Maximum delay cap
    - Retryable exception filtering

    Args:
        func: Function to retry (can be async or sync)
        config: Retry configuration
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Function result

    Raises:
        Last exception if all retries fail

    Example:
        >>> result = await retry_with_backoff(
        ...     redis_client.get,
        ...     RetryConfig(
        ...         max_attempts=3,
        ...         initial_delay=1.0,
        ...         retryable_exceptions=(ConnectionError, TimeoutError)
        ...     ),
        ...     key
        ... )
    """
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt == config.max_attempts - 1:
                # Last attempt failed
                logger.error(
                    f"[RETRY] All {config.max_attempts} attempts failed for {func.__name__}: {e}",
                    exc_info=True
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(
                config.initial_delay * (config.exponential_base ** attempt),
                config.max_delay
            )

            logger.warning(
                f"[RETRY] Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                f"Retrying in {delay:.2f}s..."
            )

            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise Exception("Retry failed: Unknown error")
