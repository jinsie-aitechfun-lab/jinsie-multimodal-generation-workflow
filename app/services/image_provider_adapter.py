from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from app.services.image_provider_retry import run_with_retry
from app.services.image_provider_types import (
    PROVIDER_API,
    PROVIDER_PILLOW,
    ImageGenerationTask,
    RetryConfig,
)


def _derive_run_seed(run_id: str) -> int:
    """Deterministic seed in [0, 9999999999] derived from run_id."""
    digest = hashlib.sha256(run_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:5], "big") % 10_000_000_000


def _img2img_enabled() -> bool:
    return (os.getenv("SILICONFLOW_IMG2IMG_ENABLED") or "").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _img2img_strength() -> float:
    raw = (os.getenv("SILICONFLOW_IMG2IMG_STRENGTH") or "0.75").strip()
    try:
        return max(0.1, min(1.0, float(raw)))
    except ValueError:
        return 0.75


class PillowStorybookAdapter:
    def __init__(self, runner: Any) -> None:
        self._runner = runner

    @property
    def provider_name(self) -> str:
        return PROVIDER_PILLOW

    @property
    def supports_reference_image(self) -> bool:
        return False

    def generate(self, task: ImageGenerationTask) -> bytes:
        scene = dict(task.prompt_metadata.get("scene") or {})
        scene_index = int(task.prompt_metadata.get("scene_index") or 1)
        ctx = task.prompt_metadata.get("ctx")
        if ctx is None:
            raise RuntimeError("pillow adapter requires ctx in prompt_metadata")

        return self._runner._build_scene_png(ctx, scene, scene_index)


class ApiImageGeneratorAdapter:
    def __init__(self, runner: Any) -> None:
        self._runner = runner

    @property
    def provider_name(self) -> str:
        return PROVIDER_API

    @property
    def supports_reference_image(self) -> bool:
        return False

    def generate(self, task: ImageGenerationTask) -> bytes:
        return self._generate_api_image_bytes(
            prompt=task.prompt,
            run_id=task.run_id,
            scene=task.prompt_metadata.get("scene") or {},
            scene_index=int(task.prompt_metadata.get("scene_index") or 1),
            negative_prompt=str(task.prompt_metadata.get("negative_prompt") or ""),
            img2img_reference_path=task.prompt_metadata.get("img2img_reference_path"),
        )

    def _generate_api_image_bytes(
        self,
        *,
        prompt: str,
        run_id: str = "",
        scene: dict[str, Any],
        scene_index: int,
        negative_prompt: str = "",
        img2img_reference_path: Optional[Any] = None,
    ) -> bytes:
        if self._runner._force_image_rate_limit():
            raise RuntimeError("HTTP 429: IPM limit reached (forced for local testing)")

        if not self._runner._api_image_enabled():
            raise RuntimeError("API_IMAGE_ENABLED is false")

        api_key = self._runner._image_api_key()
        if not api_key:
            raise RuntimeError("image api key is missing")

        base_url = self._runner._image_api_base_url()

        model = os.getenv("SILICONFLOW_IMAGE_MODEL", "Kwai-Kolors/Kolors").strip()
        if not model:
            model = "Kwai-Kolors/Kolors"

        image_size = os.getenv("SILICONFLOW_IMAGE_SIZE", "1280x720").strip()
        if not image_size:
            image_size = "1280x720"

        default_negative_prompt = os.getenv(
            "SILICONFLOW_IMAGE_NEGATIVE_PROMPT",
            (
                "low quality, blurry, distorted anatomy, broken composition, "
                "extra limbs, duplicated subject, unreadable details"
            ),
        ).strip()
        negative_prompt = self._merge_negative_prompt(
            default_negative_prompt,
            negative_prompt,
        )

        num_inference_steps_raw = os.getenv("SILICONFLOW_IMAGE_STEPS", "20").strip()
        guidance_scale_raw = os.getenv("SILICONFLOW_IMAGE_GUIDANCE", "7.5").strip()

        try:
            num_inference_steps = int(num_inference_steps_raw)
        except ValueError:
            num_inference_steps = 20

        try:
            guidance_scale = float(guidance_scale_raw)
        except ValueError:
            guidance_scale = 7.5

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "image_size": image_size,
        }

        if run_id:
            payload["seed"] = (_derive_run_seed(run_id) + scene_index) % 10_000_000_000

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        if "kolors" in model.lower():
            payload["batch_size"] = 1
            payload["num_inference_steps"] = num_inference_steps
            payload["guidance_scale"] = guidance_scale

        if _img2img_enabled() and img2img_reference_path is not None:
            ref_path = Path(img2img_reference_path)
            if ref_path.is_file():
                ref_b64 = base64.b64encode(ref_path.read_bytes()).decode("ascii")
                payload["image"] = f"data:image/png;base64,{ref_b64}"
                payload["strength"] = _img2img_strength()

        request_url = f"{base_url.rstrip('/')}/images/generations"
        request_body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            request_url,
            data=request_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        generation_retry_result = run_with_retry(
            lambda: self._request_generation_response_text(request=request),
            RetryConfig(
                max_attempts=6,
                base_delay_seconds=5.0,
                backoff_multiplier=2.0,
                retry_on_rate_limit=True,
                retry_on_network_error=True,
            ),
        )

        if generation_retry_result.ok and isinstance(generation_retry_result.value, str):
            response_text = generation_retry_result.value
        elif generation_retry_result.error is not None:
            raise generation_retry_result.error
        else:
            raise RuntimeError("SiliconFlow image generation returned empty response text")

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "SiliconFlow image generation returned invalid JSON: "
                f"{response_text[:500]}"
            ) from error

        images = result.get("images") or []
        if not images:
            raise RuntimeError(
                f"SiliconFlow image generation returned no images: {response_text[:500]}"
            )

        first_image = images[0] or {}
        image_url = str(first_image.get("url") or "").strip()
        if not image_url:
            raise RuntimeError(
                "SiliconFlow image generation returned empty image url: "
                f"{response_text[:500]}"
            )

        download_request = urllib.request.Request(
            image_url,
            headers={"User-Agent": "Mozilla/5.0"},
            method="GET",
        )

        retry_result = run_with_retry(
            lambda: self._download_generated_image_bytes(
                download_request=download_request,
                scene_index=scene_index,
            ),
            RetryConfig(
                max_attempts=6,
                base_delay_seconds=3.0,
                backoff_multiplier=2.0,
                retry_on_rate_limit=True,
                retry_on_network_error=True,
            ),
        )

        if retry_result.ok and isinstance(retry_result.value, (bytes, bytearray)):
            return bytes(retry_result.value)

        if retry_result.error is not None:
            raise retry_result.error

        raise RuntimeError(
            f"Generated image download returned empty bytes for scene {scene_index}"
        )

    def _merge_negative_prompt(self, *parts: str) -> str:
        merged: list[str] = []
        seen = set()

        for part in parts:
            for item in str(part or "").replace("；", ",").replace(";", ",").split(","):
                value = item.strip()
                if value and value not in seen:
                    merged.append(value)
                    seen.add(value)

        return ", ".join(merged)

    def _request_generation_response_text(
        self,
        *,
        request: urllib.request.Request,
    ) -> str:
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            error_body = ""
            try:
                error_body = error.read().decode("utf-8")
            except Exception:
                error_body = repr(error)
            raise RuntimeError(
                f"SiliconFlow image generation failed with HTTP {error.code}: {error_body}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"SiliconFlow image generation request failed: {error}"
            ) from error
        except Exception as error:
            raise RuntimeError(
                f"SiliconFlow image generation request failed: {error}"
            ) from error
    
    def _download_generated_image_bytes(
        self,
        *,
        download_request: urllib.request.Request,
        scene_index: int,
    ) -> bytes:
        try:
            with urllib.request.urlopen(download_request, timeout=120) as response:
                downloaded = response.read()
        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"Generated image download failed with HTTP {error.code} for scene {scene_index}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Generated image download failed for scene {scene_index}: {error}"
            ) from error
        except Exception as error:
            raise RuntimeError(
                f"Generated image download failed for scene {scene_index}: {error}"
            ) from error

        if not downloaded:
            raise RuntimeError(
                f"Generated image download returned empty bytes for scene {scene_index}"
            )

        return downloaded
