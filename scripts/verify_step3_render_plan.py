"""HTTP 契约验证：Step 3 抽取 render_plan + render_package 后行为不变。

跑法：
    python scripts/verify_step3_render_plan.py

前置：本机 8004 端口跑着 `make api`。

验证点：
1. `/v1/workflow/run` 接受包含 `render_plan` 步骤的请求，HTTP 200。
2. 后台异步跑完后，`assets/mock/<workflow_id>/outputs.json` 的
   `outputs.render_plan` 字段满足 RunnerRenderPlanSupport.build_render_plan_by_provider
   的契约（provider / scene_count / asset_plan / edit_plan）。
3. `outputs.render_package`（运行结束时由 `_render_plan.build_render_package` 拼出）
   形状正确：format / package_name / files 中含 16 个核心 key，
   且 `publish_manifest.json` / `kling_scene_package.json` / `real_samples_manifest.json`
   关键字段齐全。
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict

import requests

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8004")
WORKFLOW = "wf-step3-render"
SESSION = "sess-step3"
TOPIC = "小蜗牛运快递"
OUT_PATH = Path("assets/mock") / WORKFLOW / "outputs.json"

REQUEST_BODY = {
    "workflow_id": WORKFLOW,
    "session_id": SESSION,
    "input": {
        "topic": TOPIC,
        "duration_sec": 60,
        "voice_mode": "single",
        "video_provider": "kling",
    },
    "steps": [
        {"name": "story"},
        {"name": "storyboard"},
        {"name": "render_plan"},
    ],
}

REQUIRED_RENDER_PACKAGE_FILES = {
    "story.json",
    "storyboard.json",
    "image_prompts.json",
    "image_assets.json",
    "video_prompts.json",
    "dialogue_script.json",
    "audio_segments.json",
    "audio_directory_manifest.json",
    "audio_assets_manifest.json",
    "narration.txt",
    "subtitles.srt",
    "render_plan.json",
    "final_video.json",
    "publish_manifest.json",
    "kling_scene_package.json",
    "real_samples_manifest.json",
}


def _health() -> None:
    r = requests.get(f"{API_BASE}/health", timeout=3)
    r.raise_for_status()
    assert r.json().get("status") == "ok"


def _post_workflow() -> Dict[str, Any]:
    r = requests.post(
        f"{API_BASE}/v1/workflow/run",
        json=REQUEST_BODY,
        timeout=10,
    )
    r.raise_for_status()
    payload = r.json()
    assert payload.get("status") == "processing", payload
    return payload


def _wait_for_outputs(timeout_sec: int = 90) -> None:
    if OUT_PATH.parent.exists():
        shutil.rmtree(OUT_PATH.parent)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if OUT_PATH.exists():
            return
        time.sleep(1)
    raise TimeoutError(f"outputs.json not produced within {timeout_sec}s: {OUT_PATH}")


def _assert_render_plan_shape(render_plan: Dict[str, Any]) -> None:
    assert render_plan, "render_plan output is empty"
    assert render_plan.get("provider") == "kling", render_plan.get("provider")
    assert isinstance(render_plan.get("scene_count"), int), render_plan.get("scene_count")
    assert render_plan["scene_count"] > 0
    asset_plan = render_plan.get("asset_plan")
    assert isinstance(asset_plan, list) and len(asset_plan) == render_plan["scene_count"]
    for asset in asset_plan:
        assert set(asset.keys()) >= {
            "scene_id", "image_required", "video_required",
            "audio_required", "subtitle_required",
        }, asset
    edit_plan = render_plan.get("edit_plan") or {}
    assert edit_plan.get("adapter_status") == "pending_api_integration", edit_plan
    assert "next_step" in edit_plan


def _assert_render_package_shape(render_package: Dict[str, Any]) -> None:
    assert render_package, "render_package missing"
    assert render_package.get("format") == "render_package_v1"
    pkg_name = render_package.get("package_name") or ""
    assert pkg_name.startswith(f"{WORKFLOW}_"), pkg_name
    files = render_package.get("files") or {}
    missing = REQUIRED_RENDER_PACKAGE_FILES - set(files.keys())
    assert not missing, f"render_package missing files: {missing}"

    publish = files.get("publish_manifest.json") or {}
    assert publish.get("video_provider") == "kling", publish
    assert publish.get("topic") == TOPIC

    samples = files.get("real_samples_manifest.json") or {}
    assert samples.get("provider") == "kling"
    assert len(samples.get("samples") or []) == 1

    kling_pkg = files.get("kling_scene_package.json") or {}
    assert kling_pkg.get("provider") == "kling"
    assert "recommended_prompt" in kling_pkg


def main() -> int:
    print("=== Step 3 HTTP 契约验证 ===")
    print(f"API_BASE = {API_BASE}")

    print("[1/4] 健康检查...")
    _health()
    print("    OK")

    print("[2/4] 发送 workflow 请求（包含 render_plan step）...")
    _post_workflow()
    print(f"    OK workflow_id={WORKFLOW}")

    print("[3/4] 等待 outputs.json 产出...")
    _wait_for_outputs()
    payload = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    outputs = payload.get("outputs") or payload
    print(f"    OK keys={sorted(outputs.keys())[:8]}...")

    print("[4/4] 断言 render_plan + render_package 契约...")
    _assert_render_plan_shape(outputs.get("render_plan") or {})
    _assert_render_package_shape(payload.get("render_package") or outputs.get("render_package") or {})

    print()
    print("PASS: Step 3 HTTP 契约通过（render_plan + render_package 行为未变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
