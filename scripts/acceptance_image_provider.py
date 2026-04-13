from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict
from uuid import uuid4

import requests


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _post_json(base_url: str, path: str, payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    response = requests.post(
        f"{base_url}{path}",
        json=payload,
        timeout=timeout,
    )
    if response.status_code != 200:
        _fail(f"{path} http_status={response.status_code}, body={response.text}")
    return response.json()


def _build_run_payload(session_id: str) -> Dict[str, Any]:
    return {
        "workflow_id": "storybook-demo",
        "session_id": session_id,
        "input": {
            "topic": "小兔子的一天",
            "audience": "children",
            "tone": "warm",
            "visual_style": "storybook",
            "character_style": "animal",
            "voice_style": "warm_female",
            "voiceover_enabled": False,
            "duration_sec": 60,
            "language": "zh-CN",
            "subtitle_enabled": True,
            "video_provider": "mock",
            "output_mode": "full_video",
        },
        "steps": [
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "image_prompts"},
            {"name": "image_assets"},
            {"name": "video_prompts"},
            {"name": "render_plan"},
        ],
    }


def _build_refresh_payload(run_response: Dict[str, Any]) -> Dict[str, Any]:
    outputs = run_response.get("outputs") or {}
    return {
        "workflow_id": run_response["workflow_id"],
        "session_id": run_response.get("session_id"),
        "run_id": run_response["run_id"],
        "storyboard": outputs.get("storyboard") or {},
        "workflow_input": {},
        "image_review": outputs.get("image_review") or {},
        "video_provider": "mock",
    }


def _run_then_refresh(base_url: str, session_prefix: str) -> Dict[str, Any]:
    session_id = f"{session_prefix}-{uuid4().hex[:8]}"
    run_payload = _build_run_payload(session_id)
    run_response = _post_json(base_url, "/v1/workflow/run", run_payload)
    refresh_payload = _build_refresh_payload(run_response)
    refresh_response = _post_json(
        base_url,
        "/v1/image-review/refresh",
        refresh_payload,
    )
    return refresh_response


def _assert_generated_pillow(refresh_response: Dict[str, Any]) -> None:
    image_assets = refresh_response.get("image_assets") or {}
    image_review = refresh_response.get("image_review") or {}
    video_prompts = refresh_response.get("video_prompts") or {}

    if image_assets.get("provider") != "pillow_storybook_renderer":
        _fail(f"expected pillow provider, got: {image_assets}")

    asset_count = image_assets.get("asset_count")
    if not isinstance(asset_count, int) or asset_count <= 0:
        _fail(f"expected asset_count > 0, got: {image_assets}")

    if image_assets.get("status") in {"pending", "retrying", "failed"}:
        _fail(f"unexpected non-generated image_assets status: {image_assets}")

    assets = image_assets.get("assets") or []
    if not isinstance(assets, list) or not assets:
        _fail(f"expected non-empty assets list, got: {image_assets}")

    first = assets[0]
    candidates = first.get("candidate_asset_refs") or []
    if len(candidates) != 2:
        _fail(f"expected 2 candidate assets, got: {first}")

    if candidates[0].get("provider") != "pillow_storybook_renderer":
        _fail(f"expected pillow candidate provider, got: {first}")

    if image_review.get("mode") != "selection_contract":
        _fail(f"expected selection_contract image_review mode, got: {image_review}")

    if video_prompts.get("status") in {"pending", "retrying"}:
        _fail(f"unexpected pending video_prompts on generated path: {video_prompts}")

    _ok("pillow generated path")


def _assert_retrying_pending(refresh_response: Dict[str, Any]) -> None:
    image_assets = refresh_response.get("image_assets") or {}
    video_prompts = refresh_response.get("video_prompts") or {}

    if image_assets.get("provider") != "api_image_generator":
        _fail(f"expected api_image_generator provider, got: {image_assets}")

    if image_assets.get("status") not in {"pending", "retrying"}:
        _fail(f"expected pending/retrying image_assets status, got: {image_assets}")

    if image_assets.get("reason") not in {"rate_limited", "deferred_to_refresh"}:
        _fail(f"expected rate-limited style reason, got: {image_assets}")

    retry_after_sec = image_assets.get("retry_after_sec")
    if retry_after_sec != 60:
        _fail(f"expected retry_after_sec=60, got: {image_assets}")

    asset_count = image_assets.get("asset_count")
    if asset_count not in {0, None}:
        _fail(f"expected empty/pending asset_count, got: {image_assets}")

    if video_prompts.get("status") != "pending":
        _fail(f"expected pending video_prompts, got: {video_prompts}")

    if video_prompts.get("reason") != "waiting_for_image_assets":
        _fail(f"expected waiting_for_image_assets reason, got: {video_prompts}")

    _ok("api retrying/pending path")


def _assert_fallback_to_pillow(refresh_response: Dict[str, Any]) -> None:
    image_assets = refresh_response.get("image_assets") or {}
    fallback = image_assets.get("fallback") or {}
    assets = image_assets.get("assets") or []

    if image_assets.get("provider") != "pillow_storybook_renderer":
        _fail(f"expected pillow provider after fallback, got: {image_assets}")

    asset_count = image_assets.get("asset_count")
    if not isinstance(asset_count, int) or asset_count <= 0:
        _fail(f"expected generated fallback assets, got: {image_assets}")

    if fallback.get("from_provider") != "api_image_generator":
        _fail(f"expected fallback from api_image_generator, got: {image_assets}")

    if fallback.get("to_provider") != "pillow_storybook_renderer":
        _fail(f"expected fallback to pillow_storybook_renderer, got: {image_assets}")

    fallback_reason = str(fallback.get("reason") or "")
    if "429" not in fallback_reason and "rate" not in fallback_reason.lower():
        _fail(f"expected rate-limit style fallback reason, got: {image_assets}")

    if not isinstance(assets, list) or not assets:
        _fail(f"expected non-empty assets list on fallback path, got: {image_assets}")

    first = assets[0]
    candidates = first.get("candidate_asset_refs") or []
    if not candidates:
        _fail(f"expected candidate assets on fallback path, got: {first}")

    if candidates[0].get("provider") != "pillow_storybook_renderer":
        _fail(f"expected pillow candidate provider after fallback, got: {first}")

    _ok("api fallback to pillow path")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8004")
    parser.add_argument(
        "--mode",
        choices=["pillow", "pending", "fallback"],
        required=True,
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    if args.mode == "pillow":
        response = _run_then_refresh(base_url, "image-provider-pillow")
        _assert_generated_pillow(response)
        return

    if args.mode == "pending":
        response = _run_then_refresh(base_url, "image-provider-pending")
        _assert_retrying_pending(response)
        return

    if args.mode == "fallback":
        response = _run_then_refresh(base_url, "image-provider-fallback")
        _assert_fallback_to_pillow(response)
        return

    _fail(f"unknown mode: {args.mode}")


if __name__ == "__main__":
    main()