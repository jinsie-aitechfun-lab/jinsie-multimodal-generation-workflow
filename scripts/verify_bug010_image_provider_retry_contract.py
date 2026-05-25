from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.image_provider_retry import should_retry
from app.services.image_provider_types import RetryConfig


def main() -> int:
    config = RetryConfig(
        max_attempts=6,
        base_delay_seconds=0.0,
        backoff_multiplier=1.0,
        retry_on_rate_limit=True,
        retry_on_network_error=True,
    )

    retryable_errors = [
        RuntimeError(
            "SiliconFlow image generation failed with HTTP 500: "
            '{"code":50507,"message":"Request failed: Unknown error","data":null}'
        ),
        RuntimeError("HTTP 502: IMAGE_GENERATION_FAILED"),
        RuntimeError("Generated image download failed with HTTP 504 for scene 1"),
    ]
    non_retryable_error = RuntimeError(
        "SiliconFlow image generation failed with HTTP 400: bad request"
    )

    failures: list[str] = []

    for error in retryable_errors:
        if not should_retry(error, config):
            failures.append(f"expected retryable: {error}")

    if should_retry(non_retryable_error, config):
        failures.append("HTTP 400 should not be retried as a transient provider error")

    if failures:
        print("SUMMARY = FAIL")
        for failure in failures:
            print("-", failure)
        return 1

    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
