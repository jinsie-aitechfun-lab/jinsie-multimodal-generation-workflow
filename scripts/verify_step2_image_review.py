"""HTTP-layer verification for runner refactor Step 2 (RunnerImageReviewSupport).

Fires one async /v1/workflow/run request that includes the
"image_assets" step. This triggers two of the extracted methods inside
the runner's main loop:

    RunnerImageReviewSupport.build_deferred_image_assets_output()
    RunnerImageReviewSupport.build_pending_image_review()

After the run finishes (outputs.json is written to disk), this script
asserts that the resulting `image_assets` and `image_review` payloads
have the exact shape produced by those methods. If the runner ever
silently drops back to the old `self._build_*` method names or any
call site goes stale, the assertions below will fail loudly.

Usage:
    # In one terminal:
    make api

    # In another terminal:
    python scripts/verify_step2_image_review.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8004")
WORKFLOW = "wf-step2-image-review"
SESSION = "sess-step2"
TOPIC = "小白兔种萝卜"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "assets" / "mock" / WORKFLOW / "outputs.json"
MAX_WAIT_SECONDS = 180
POLL_INTERVAL = 2


def _post_workflow() -> dict:
    payload = {
        "workflow_id": WORKFLOW,
        "session_id": SESSION,
        "input": {
            "topic": TOPIC,
            "duration_sec": 60,
            "voice_mode": "single",
        },
        "steps": [
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "image_prompts"},
            {"name": "image_assets"},
        ],
    }
    resp = requests.post(f"{API_BASE}/v1/workflow/run", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _wait_for_outputs() -> None:
    deadline = time.time() + MAX_WAIT_SECONDS
    waited = 0
    while time.time() < deadline:
        if OUT_PATH.exists():
            print(f"workflow 已完成（用时 ~{waited} 秒）")
            return
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
    raise SystemExit(
        f"FAIL: workflow 在 {MAX_WAIT_SECONDS} 秒内未完成（{OUT_PATH} 不存在）"
    )


def _assert_image_assets_shape(image_assets: dict) -> None:
    """image_assets 字段应符合 build_deferred_image_assets_output() 的输出契约."""
    required_top = {
        "enabled",
        "run_id",
        "provider",
        "provider_capabilities",
        "status",
        "reason",
        "asset_count",
        "assets",
    }
    missing = required_top - set(image_assets.keys())
    assert not missing, f"image_assets 缺字段: {missing}"
    assert image_assets["enabled"] is False, "deferred output 的 enabled 必须是 False"
    assert image_assets["status"] == "pending", "deferred output 的 status 必须是 pending"
    assert image_assets["reason"] == "deferred_to_refresh", (
        f"deferred output 的 reason 必须是 deferred_to_refresh, got {image_assets['reason']!r}"
    )
    assert image_assets["asset_count"] == 0
    assert image_assets["assets"] == []
    caps = image_assets["provider_capabilities"]
    assert caps.get("supports_reference_image") is False
    assert caps.get("reference_image_mode") == "metadata_only"
    print(
        "[OK] image_assets 字段结构匹配 build_deferred_image_assets_output() 契约"
    )


def _assert_image_review_shape(image_review: dict) -> None:
    """image_review 字段应符合 build_pending_image_review() 的输出契约."""
    required = {"enabled", "status", "reason", "selected_assets"}
    missing = required - set(image_review.keys())
    assert not missing, f"image_review 缺字段: {missing}"
    assert image_review["enabled"] is False, "pending review 的 enabled 必须是 False"
    assert image_review["status"] == "pending", "pending review 的 status 必须是 pending"
    assert image_review["reason"] == "waiting_for_manual_refresh", (
        "image_assets step 之后 image_review 的 reason 应该是 "
        f"waiting_for_manual_refresh, got {image_review['reason']!r}"
    )
    assert image_review["selected_assets"] == [], (
        "pending review 的 selected_assets 必须是空 list"
    )
    print("[OK] image_review 字段结构匹配 build_pending_image_review() 契约")


def main() -> int:
    if OUT_PATH.exists():
        OUT_PATH.unlink()

    print("=== 健康检查 ===")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5).json()
    except Exception as exc:
        print(f"API 未启动：先在另一个终端跑 make api ({exc})")
        return 2
    print(health)
    print()

    print(f"=== 发送请求 (workflow={WORKFLOW}, topic={TOPIC}, 含 image_assets step) ===")
    print(_post_workflow())
    _wait_for_outputs()
    print()

    with OUT_PATH.open("r", encoding="utf-8") as f:
        response_payload = json.load(f)

    # outputs.json mirrors the WorkflowRunResponse model, where the runner's
    # aggregated_outputs dict (containing image_assets, image_review, etc.)
    # is nested under the top-level `outputs` key.
    aggregated_outputs = response_payload.get("outputs") or {}
    image_assets = aggregated_outputs.get("image_assets")
    image_review = aggregated_outputs.get("image_review")

    assert image_assets is not None, (
        "outputs.outputs.image_assets 字段不存在！"
        f" Top-level keys: {sorted(response_payload.keys())}"
    )
    assert image_review is not None, (
        "outputs.outputs.image_review 字段不存在！"
        f" outputs keys: {sorted(aggregated_outputs.keys())}"
    )

    print("=== 验证 image_assets 输出契约 ===")
    _assert_image_assets_shape(image_assets)
    print()
    print("=== 验证 image_review 输出契约 ===")
    _assert_image_review_shape(image_review)
    print()
    print("PASS: HTTP 层 RunnerImageReviewSupport 工作正常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
