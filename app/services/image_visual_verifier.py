from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_VISION_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"


def visual_review_enabled() -> bool:
    value = (os.getenv("IMAGE_REVIEW_VISION_ENABLED") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def vision_model_name() -> str:
    return (
        os.getenv("IMAGE_REVIEW_VISION_MODEL")
        or os.getenv("OPENAI_VISION_MODEL")
        or os.getenv("VISION_MODEL")
        or DEFAULT_VISION_MODEL
    ).strip()


def _api_base_url() -> str:
    return (
        os.getenv("IMAGE_REVIEW_VISION_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("LLM_API_BASE_URL")
        or "https://api.siliconflow.cn/v1"
    ).strip()


def _api_key() -> str:
    return (
        os.getenv("IMAGE_REVIEW_VISION_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("SILICONFLOW_API_KEY")
        or os.getenv("IMAGE_API_KEY")
        or ""
    ).strip()


def _timeout_seconds() -> int:
    raw = (os.getenv("IMAGE_REVIEW_VISION_TIMEOUT_SECONDS") or "").strip()
    if raw.isdigit():
        return max(5, min(180, int(raw)))
    return 60


def _character_summary(characters: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in characters or []:
        if not isinstance(item, dict):
            continue

        name = str(item.get("display_name") or item.get("species") or "").strip()
        species = str(item.get("species") or "").strip()
        traits = item.get("signature_traits") or item.get("visual_traits") or []
        forbidden = item.get("forbidden_traits") or []
        if isinstance(traits, list):
            traits_text = ", ".join(str(value).strip() for value in traits if str(value).strip())
        else:
            traits_text = str(traits or "").strip()
        if isinstance(forbidden, list):
            forbidden_text = ", ".join(
                str(value).strip() for value in forbidden if str(value).strip()
            )
        else:
            forbidden_text = str(forbidden or "").strip()

        parts = [
            f"name={name}" if name else "",
            f"species={species}" if species else "",
            f"must_keep={traits_text}" if traits_text else "",
            f"must_avoid={forbidden_text}" if forbidden_text else "",
        ]
        line = "; ".join(part for part in parts if part)
        if line:
            lines.append(f"- {line}")
    return "\n".join(lines)


def _image_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _extract_json_object(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(raw[start : end + 1])

    return data if isinstance(data, dict) else {}


class OpenAICompatibleImageVisualVerifier:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def evaluate(
        self,
        *,
        image_path: Path,
        prompt: str,
        characters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        character_summary = _character_summary(characters)
        instruction = (
            "You are a strict visual reviewer for children's story image candidates.\n"
            "Return ONLY compact JSON with these keys: score, passed, "
            "missing_required_characters, forbidden_trait_issues, anatomy_leakage_issues, notes.\n"
            "Score from 0 to 100. Penalize missing required characters, merged characters, "
            "wrong species, and traits transferred between characters.\n"
            f"Scene prompt:\n{prompt}\n\nRequired characters:\n{character_summary or '- none'}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {
                            "type": "image_url",
                            "image_url": {"url": _image_data_url(image_path)},
                        },
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": 500,
        }

        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read()

        data = json.loads(raw.decode("utf-8", errors="ignore"))
        content = (
            (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
            or ""
        )
        result = _extract_json_object(content)
        result["provider"] = "openai_compatible_vision"
        result["model"] = self.model
        return result


def build_env_visual_verifier() -> Optional[OpenAICompatibleImageVisualVerifier]:
    if not visual_review_enabled():
        return None

    model = vision_model_name()
    api_key = _api_key()
    if not model or not api_key:
        return None

    return OpenAICompatibleImageVisualVerifier(
        api_key=api_key,
        base_url=_api_base_url(),
        model=model,
        timeout_seconds=_timeout_seconds(),
    )
