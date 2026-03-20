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


def _run_request(base_url: str, session_id: str, topic: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "workflow_id": "storybook-demo",
        "session_id": session_id,
        "input": {
            "topic": topic,
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
    return r.json()


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

    # 2) first run
    resp1 = _run_request(base_url, "acceptance-session-001", "小兔子的一天")

    if resp1.get("workflow_id") != "storybook-demo":
        _fail(f"workflow_id mismatch: {resp1.get('workflow_id')}")
    if resp1.get("session_id") != "acceptance-session-001":
        _fail(f"session_id mismatch: {resp1.get('session_id')}")
    if not str(resp1.get("run_id", "")).startswith("run_"):
        _fail(f"run_id invalid: {resp1.get('run_id')}")
    if resp1.get("status") != "COMPLETED":
        _fail(f"status != COMPLETED: {resp1.get('status')}")

    steps = resp1.get("steps")
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

    outputs = resp1.get("outputs") or {}
    for key in expected_names:
        if key not in outputs:
            _fail(f"missing output key: {key}")

    memory1 = resp1.get("session_memory_summary") or {}
    if memory1.get("enabled") is not True:
        _fail(f"session_memory_summary.enabled invalid: {memory1}")
    if memory1.get("has_previous_session") is not False:
        _fail(f"first request should have no previous session: {memory1}")

    # 3) second run with same session id
    resp2 = _run_request(base_url, "acceptance-session-001", "小兔子的新冒险")
    memory2 = resp2.get("session_memory_summary") or {}

    if memory2.get("enabled") is not True:
        _fail(f"second session memory not enabled: {memory2}")
    if memory2.get("has_previous_session") is not True:
        _fail(f"second request should detect previous session: {memory2}")
    if memory2.get("previous_topic") != "小兔子的一天":
        _fail(f"previous_topic mismatch: {memory2}")
    if memory2.get("previous_scene_count") != 4:
        _fail(f"previous_scene_count mismatch: {memory2}")

    _ok("/v1/workflow/run")
    print(json.dumps(resp2, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()