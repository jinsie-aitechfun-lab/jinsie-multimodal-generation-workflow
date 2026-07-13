"""Contract verification for async workflow status polling.

Usage:
    python scripts/verify_perf001_workflow_status_contract.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app.main as main_app
from fastapi.testclient import TestClient


def make_payload(workflow_id: str) -> dict:
    return {
        "workflow_id": workflow_id,
        "session_id": f"{workflow_id}_session",
        "input": {
            "topic": "小兔子的一天",
            "duration_sec": 60,
            "video_provider": "mock",
        },
        "steps": [{"name": "story"}],
    }


def main() -> int:
    original_assets_dir = main_app.ASSETS_DIR
    original_run_async = main_app._runner._run_async

    try:
        with TemporaryDirectory() as tmp_dir:
            main_app.ASSETS_DIR = Path(tmp_dir)
            client = TestClient(main_app.app)

            captured = {}

            def pending_run_async(
                run_input,
                callback,
                error_callback=None,
                progress_callback=None,
            ):
                captured["run_input"] = run_input
                captured["callback"] = callback
                captured["error_callback"] = error_callback
                captured["progress_callback"] = progress_callback

            main_app._runner._run_async = pending_run_async

            response = client.post(
                "/v1/workflow/run",
                json=make_payload("wf_verify_status_processing"),
            )
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "processing"

            status_response = client.get(
                "/v1/workflow/status/wf_verify_status_processing"
            )
            assert status_response.status_code == 200, status_response.text
            processing_body = status_response.json()
            assert processing_body["status"] == "processing"
            assert processing_body["current_step"] == "story"
            assert processing_body["completed_steps"] == 0
            assert processing_body["total_steps"] == 1

            captured["progress_callback"](
                {
                    "current_step": "story",
                    "current_step_index": 1,
                    "completed_steps": 0,
                    "total_steps": 1,
                    "progress_percent": 0,
                }
            )
            progress_response = client.get(
                "/v1/workflow/status/wf_verify_status_processing"
            )
            assert progress_response.status_code == 200, progress_response.text
            assert progress_response.json()["current_step"] == "story"

            captured["callback"](
                {
                    "workflow_id": "wf_verify_status_processing",
                    "status": "COMPLETED",
                    "outputs": {"story": {"title": "小兔子的一天"}},
                }
            )

            completed_response = client.get(
                "/v1/workflow/status/wf_verify_status_processing"
            )
            assert completed_response.status_code == 200, completed_response.text
            assert completed_response.json()["status"] == "completed"

            outputs_path = (
                Path(tmp_dir)
                / "mock"
                / "wf_verify_status_processing"
                / "outputs.json"
            )
            with open(outputs_path, "r", encoding="utf-8") as f:
                outputs_payload = json.load(f)
            assert outputs_payload["outputs"]["story"]["title"] == "小兔子的一天"

            def failing_run_async(
                run_input,
                callback,
                error_callback=None,
                progress_callback=None,
            ):
                assert error_callback is not None
                error_callback(RuntimeError("provider timeout"))

            main_app._runner._run_async = failing_run_async
            failed_run = client.post(
                "/v1/workflow/run",
                json=make_payload("wf_verify_status_failed"),
            )
            assert failed_run.status_code == 200, failed_run.text

            failed_status = client.get("/v1/workflow/status/wf_verify_status_failed")
            assert failed_status.status_code == 200, failed_status.text
            failed_body = failed_status.json()
            assert failed_body["status"] == "failed"
            assert "provider timeout" in failed_body["message"]
    finally:
        main_app.ASSETS_DIR = original_assets_dir
        main_app._runner._run_async = original_run_async

    print("[OK] workflow status endpoint reports processing and completed")
    print("[OK] workflow status endpoint reports async failures")
    print("PASS: PERF-001 workflow status polling contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
