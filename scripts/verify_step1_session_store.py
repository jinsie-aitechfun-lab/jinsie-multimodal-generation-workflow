"""HTTP-layer verification for runner refactor Step 1 (RunnerSessionStore).

Fires two async /v1/workflow/run requests with DIFFERENT workflow_ids
but the SAME session_id, waits for each to finish writing its
outputs.json on disk, then asserts that the second response's
session_memory_summary correctly recalls the first request's topic.

This proves that RunnerSessionStore preserves cross-request session
memory through the full FastAPI -> async thread -> WorkflowRunner.run()
path with real LLM-backed story generation.

Usage:
    # In one terminal:
    make api

    # In another terminal:
    python scripts/verify_step1_session_store.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8004")
WF_A = "wf-step1-a"
WF_B = "wf-step1-b"
SESSION = "sess-step1"
TOPIC_A = "小白兔吃萝卜"
TOPIC_B = "小白兔种萝卜"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_A = PROJECT_ROOT / "assets" / "mock" / WF_A / "outputs.json"
OUT_B = PROJECT_ROOT / "assets" / "mock" / WF_B / "outputs.json"
MAX_WAIT_SECONDS = 120
POLL_INTERVAL = 2


def _post_workflow(workflow_id: str, session_id: str, topic: str) -> dict:
    payload = {
        "workflow_id": workflow_id,
        "session_id": session_id,
        "input": {
            "topic": topic,
            "duration_sec": 60,
            "voice_mode": "single",
        },
        "steps": [{"name": "story"}, {"name": "storyboard"}],
    }
    resp = requests.post(f"{API_BASE}/v1/workflow/run", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _wait_for_outputs(path: Path, label: str) -> None:
    deadline = time.time() + MAX_WAIT_SECONDS
    waited = 0
    while time.time() < deadline:
        if path.exists():
            print(f"{label} 已完成（用时 ~{waited} 秒）")
            return
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
    raise SystemExit(f"FAIL: {label} 在 {MAX_WAIT_SECONDS} 秒内未完成（{path} 不存在）")


def main() -> int:
    # Clean previous artifacts so the polling loop is meaningful.
    for path in (OUT_A, OUT_B):
        if path.exists():
            path.unlink()

    print("=== 健康检查 ===")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5).json()
    except Exception as exc:
        print(f"API 未启动：先在另一个终端跑 make api ({exc})")
        return 2
    print(health)
    print()

    print(
        f"=== 第 1 次请求 (workflow={WF_A}, session={SESSION}, topic={TOPIC_A}) ==="
    )
    print(_post_workflow(WF_A, SESSION, TOPIC_A))
    _wait_for_outputs(OUT_A, "第 1 次")
    print()

    print(
        f"=== 第 2 次请求 (workflow={WF_B}, 同一个 session={SESSION}, topic={TOPIC_B}) ==="
    )
    print(_post_workflow(WF_B, SESSION, TOPIC_B))
    _wait_for_outputs(OUT_B, "第 2 次")
    print()

    print("=== 第 2 次的 session_memory_summary ===")
    with OUT_B.open("r", encoding="utf-8") as f:
        data = json.load(f)
    summary = data.get("session_memory_summary", {})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print()

    if (
        summary.get("has_previous_session") is True
        and summary.get("previous_topic") == TOPIC_A
    ):
        print("PASS: HTTP 层 session memory 工作正常")
        return 0

    print(
        "FAIL: has_previous_session="
        f"{summary.get('has_previous_session')!r}, "
        f"previous_topic={summary.get('previous_topic')!r}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
