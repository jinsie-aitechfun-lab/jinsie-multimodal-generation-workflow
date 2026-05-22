"""Contract verification for refresh-scene error responses.

Usage:
    python scripts/verify_bug002_refresh_scene_error_detail.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app.main as main_app
from fastapi.testclient import TestClient


def main() -> int:
    original_refresh = main_app._runner.refresh_image_review_scene

    def failing_refresh_scene(**kwargs):
        raise RuntimeError("api image provider timeout")

    main_app._runner.refresh_image_review_scene = failing_refresh_scene

    try:
        client = TestClient(main_app.app)
        response = client.post(
            "/v1/image-review/refresh-scene",
            json={
                "workflow_id": "wf_verify_bug002",
                "session_id": "sess_verify_bug002",
                "run_id": "run_verify_bug002",
                "scene_id": "scene_02",
                "storyboard": {"scenes": [{"scene_id": "scene_02"}]},
                "workflow_input": {
                    "topic": "小兔子的一天",
                    "duration_sec": 60,
                    "video_provider": "mock",
                },
                "image_review": {},
                "character_manifest": {},
                "image_prompts": {},
                "video_provider": "mock",
            },
        )
    finally:
        main_app._runner.refresh_image_review_scene = original_refresh

    assert response.status_code == 502, response.text
    body = response.json()
    detail = body.get("detail") or {}
    assert detail.get("code") == "IMAGE_GENERATION_FAILED", body
    assert detail.get("scene_id") == "scene_02", body
    assert detail.get("provider"), body
    assert "api image provider timeout" in detail.get("message", ""), body

    print("[OK] refresh-scene runtime errors return structured JSON detail")
    print("PASS: BUG-002 refresh-scene error detail contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
