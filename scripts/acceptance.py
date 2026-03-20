import argparse
import json
import sys
from typing import Any, Dict

import requests


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8004")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    # 1) /health
    r = requests.get(f"{base_url}/health", timeout=5)
    if r.status_code != 200:
        _fail(f"/health http_status={r.status_code}")
    body = r.json()
    if body.get("status") != "ok":
        _fail(f"/health body.status != ok, body={body}")
    _ok("/health")

    # 2) /v1/workflow/run
    payload: Dict[str, Any] = {
        "workflow_id": "storybook-demo",
        "session_id": "acceptance-session-001",
        "input": {
            "topic": "小兔子的一天",
            "audience": "children",
            "tone": "warm",
            "visual_style": "storybook",
            "character_style": "animal",
            "voice_style": "warm_female",
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
            {"name": "video_prompts"},
            {"name": "narration"},
            {"name": "subtitles"},
            {"name": "render_plan"},
        ],
    }

    r = requests.post(f"{base_url}/v1/workflow/run", json=payload, timeout=15)
    if r.status_code != 200:
        _fail(f"/v1/workflow/run http_status={r.status_code}, body={r.text}")

    resp = r.json()

    if resp.get("workflow_id") != "storybook-demo":
        _fail(f"workflow_id mismatch: {resp.get('workflow_id')}")
    if resp.get("session_id") != "acceptance-session-001":
        _fail(f"session_id mismatch: {resp.get('session_id')}")
    if not str(resp.get("run_id", "")).startswith("run_"):
        _fail(f"run_id invalid: {resp.get('run_id')}")
    if resp.get("status") != "COMPLETED":
        _fail(f"status != COMPLETED: {resp.get('status')}")

    steps = resp.get("steps")
    if not isinstance(steps, list) or len(steps) != 7:
        _fail(f"steps invalid len: {steps}")

    expected_names = [
        "story",
        "storyboard",
        "image_prompts",
        "video_prompts",
        "narration",
        "subtitles",
        "render_plan",
    ]
    actual_names = [step.get("name") for step in steps]
    if actual_names != expected_names:
        _fail(f"step names mismatch: {actual_names}")

    outputs = resp.get("outputs") or {}
    for key in expected_names:
        if key not in outputs:
            _fail(f"missing output key: {key}")

    storyboard = outputs.get("storyboard") or {}
    scenes = storyboard.get("scenes")
    if not isinstance(scenes, list) or len(scenes) == 0:
        _fail(f"storyboard.scenes invalid: {scenes}")

    narration = outputs.get("narration") or {}
    if not narration.get("full_text"):
        _fail(f"narration.full_text missing: {narration}")

    subtitles = outputs.get("subtitles") or {}
    if subtitles.get("enabled") is not True:
        _fail(f"subtitles.enabled invalid: {subtitles}")

    render_plan = outputs.get("render_plan") or {}
    if render_plan.get("provider") != "mock":
        _fail(f"render_plan.provider invalid: {render_plan}")

    _ok("/v1/workflow/run")
    print(json.dumps(resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()