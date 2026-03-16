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
        "input": {"topic": "小兔子的一天", "audience": "children"},
        "steps": [{"name": "story"}, {"name": "image"}, {"name": "audio"}, {"name": "video"}],
    }

    r = requests.post(f"{base_url}/v1/workflow/run", json=payload, timeout=15)
    if r.status_code != 200:
        _fail(f"/v1/workflow/run http_status={r.status_code}, body={r.text}")

    resp = r.json()

    if resp.get("workflow_id") != "storybook-demo":
        _fail(f"workflow_id mismatch: {resp.get('workflow_id')}")
    if not str(resp.get("run_id", "")).startswith("run_"):
        _fail(f"run_id invalid: {resp.get('run_id')}")
    if resp.get("status") != "COMPLETED":
        _fail(f"status != COMPLETED: {resp.get('status')}")

    steps = resp.get("steps")
    if not isinstance(steps, list) or len(steps) != 4:
        _fail(f"steps invalid len: {steps}")

    if steps[0].get("name") != "story":
        _fail(f"steps[0].name != story: {steps[0]}")
    if steps[-1].get("name") != "video":
        _fail(f"steps[-1].name != video: {steps[-1]}")

    _ok("/v1/workflow/run")
    print(json.dumps(resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()