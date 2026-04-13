from __future__ import annotations

import time
from typing import Any, Callable

from app.services.image_provider_types import RetryConfig, RetryResult


def is_rate_limit_error(error: Exception) -> bool:
    message = str(error or "").lower()
    if "429" in message:
        return True
    if "rate limit" in message:
        return True
    if "too many requests" in message:
        return True
    if "ipm limit" in message:
        return True
    return False


def should_retry(error: Exception, config: RetryConfig) -> bool:
    message = str(error or "").lower()

    if config.retry_on_rate_limit and is_rate_limit_error(error):
        return True

    if config.retry_on_network_error:
        network_markers = [
            "timed out",
            "timeout",
            "temporarily unavailable",
            "connection reset",
            "connection refused",
            "urlopen error",
            "remote end closed connection",
            "name or service not known",
            "nodename nor servname provided",
            "http error 500",
            "http error 502",
            "http error 503",
            "http error 504",
        ]
        if any(marker in message for marker in network_markers):
            return True

    return False


def compute_backoff_delay(
    *,
    attempt_index: int,
    base_delay_seconds: float,
    backoff_multiplier: float,
) -> float:
    if attempt_index <= 0:
        return base_delay_seconds
    return base_delay_seconds * (backoff_multiplier ** attempt_index)


def run_with_retry(
    operation: Callable[[], Any],
    config: RetryConfig,
) -> RetryResult:
    last_error: Exception | None = None
    last_delay_seconds = 0.0

    for attempt in range(1, config.max_attempts + 1):
        try:
            value = operation()
            return RetryResult(
                ok=True,
                value=value,
                error=None,
                attempts=attempt,
                last_delay_seconds=last_delay_seconds,
            )
        except Exception as error:
            last_error = error

            if attempt >= config.max_attempts or not should_retry(error, config):
                return RetryResult(
                    ok=False,
                    value=None,
                    error=error,
                    attempts=attempt,
                    last_delay_seconds=last_delay_seconds,
                )

            delay_seconds = compute_backoff_delay(
                attempt_index=attempt - 1,
                base_delay_seconds=config.base_delay_seconds,
                backoff_multiplier=config.backoff_multiplier,
            )
            last_delay_seconds = delay_seconds
            time.sleep(delay_seconds)

    return RetryResult(
        ok=False,
        value=None,
        error=last_error,
        attempts=config.max_attempts,
        last_delay_seconds=last_delay_seconds,
    )