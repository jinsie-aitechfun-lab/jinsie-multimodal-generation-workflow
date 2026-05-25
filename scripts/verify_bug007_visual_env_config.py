from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.image_visual_verifier import (
    DEFAULT_VISION_MODEL,
    build_env_visual_verifier,
    vision_model_name,
)


TRACKED_ENV_KEYS = [
    "IMAGE_REVIEW_VISION_ENABLED",
    "IMAGE_REVIEW_VISION_MODEL",
    "OPENAI_VISION_MODEL",
    "VISION_MODEL",
    "IMAGE_REVIEW_VISION_API_KEY",
    "OPENAI_API_KEY",
    "LLM_API_KEY",
    "SILICONFLOW_API_KEY",
    "IMAGE_API_KEY",
    "IMAGE_REVIEW_VISION_BASE_URL",
    "OPENAI_BASE_URL",
    "LLM_API_BASE_URL",
]


def main() -> int:
    original_env = {key: os.environ.get(key) for key in TRACKED_ENV_KEYS}

    try:
        for key in TRACKED_ENV_KEYS:
            os.environ.pop(key, None)

        os.environ["IMAGE_REVIEW_VISION_ENABLED"] = "true"
        os.environ["SILICONFLOW_API_KEY"] = "test-key"
        os.environ["OPENAI_BASE_URL"] = "https://api.siliconflow.cn/v1"

        verifier = build_env_visual_verifier()
        failures: list[str] = []

        print("vision_model_name =", vision_model_name())
        print("verifier_model =", getattr(verifier, "model", None))
        print("verifier_base_url =", getattr(verifier, "base_url", None))

        if vision_model_name() != DEFAULT_VISION_MODEL:
            failures.append("vision_model_name should fall back to the default vision model")
        if verifier is None:
            failures.append("visual verifier should be created with fallback SiliconFlow key")
        elif verifier.model != DEFAULT_VISION_MODEL:
            failures.append("visual verifier should use the default vision model")

        os.environ["IMAGE_REVIEW_VISION_MODEL"] = "custom-vision-model"
        if vision_model_name() != "custom-vision-model":
            failures.append("explicit IMAGE_REVIEW_VISION_MODEL should override the default")

        if failures:
            print("SUMMARY = FAIL")
            for failure in failures:
                print("-", failure)
            return 1

        print("SUMMARY = PASS")
        return 0
    finally:
        for key in TRACKED_ENV_KEYS:
            value = original_env.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    raise SystemExit(main())
