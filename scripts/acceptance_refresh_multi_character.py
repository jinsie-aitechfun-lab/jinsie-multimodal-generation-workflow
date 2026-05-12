from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

DEFAULT_BASE_URL = "http://127.0.0.1:8004"


def _post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    req = urllib_request.Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTPError {e.code}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"URLError: {e}") from e


def _wait_for_outputs(workflow_id: str, timeout_sec: int = 180) -> Path:
    path = Path("assets/mock") / workflow_id / "outputs.json"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if path.exists():
            return path
        time.sleep(2)
    raise TimeoutError(f"outputs.json not ready: {path}")


def _manifest_name_map(outputs: dict[str, Any]) -> dict[str, str]:
    manifest = outputs.get("character_manifest") or {}
    items = manifest.get("characters") or []
    result: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        character_id = str(item.get("character_id") or "").strip()
        display_name = str(item.get("display_name") or "").strip()
        species = str(item.get("species") or "").strip()
        name = display_name or species
        if character_id and name:
            result[character_id] = name
    return result


def _required_names_from_asset(asset: dict[str, Any], name_map: dict[str, str]) -> list[str]:
    names: list[str] = []
    for binding in asset.get("characters") or []:
        if not isinstance(binding, dict):
            continue
        character_id = str(binding.get("character_id") or "").strip()
        name = name_map.get(character_id)
        if name and name not in names:
            names.append(name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="Acceptance for multi-character refresh generation.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--topic", default="小兔子和小乌龟赛跑")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--timeout-sec", type=int, default=240)
    args = parser.parse_args()

    workflow_id = f"acceptance_refresh_multi_{int(time.time() * 1000)}"
    session_id = f"{workflow_id}_session"

    run_payload = {
        "workflow_id": workflow_id,
        "session_id": session_id,
        "steps": [
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "sentence_shots"},
            {"name": "image_prompts"},
            {"name": "image_assets"},
        ],
        "input": {
            "topic": args.topic,
            "duration_sec": args.duration,
            "audience": "children",
            "tone": "warm",
            "visual_style": "storybook",
            "character_style": "animal",
            "language": "zh-CN",
            "audio_enabled": False,
            "voiceover_enabled": False,
            "render_mode": "manual",
        },
    }

    print("workflow_id =", workflow_id)
    print("topic =", args.topic)

    run_resp = _post_json(f"{args.base_url.rstrip('/')}/v1/workflow/run", run_payload, timeout=120)
    print("run_response =", json.dumps(run_resp, ensure_ascii=False))

    outputs_path = _wait_for_outputs(workflow_id, timeout_sec=args.timeout_sec)
    data = json.loads(outputs_path.read_text(encoding="utf-8"))
    outputs = data.get("outputs") or {}

    refresh_payload = {
        "workflow_id": data.get("workflow_id"),
        "session_id": data.get("session_id"),
        "run_id": data.get("run_id"),
        "storyboard": outputs.get("storyboard") or {},
        "workflow_input": run_payload["input"],
        "image_review": outputs.get("image_review") or {},
        "video_provider": run_payload["input"].get("video_provider", "mock"),
    }

    refresh_resp = _post_json(
        f"{args.base_url.rstrip('/')}/v1/image-review/refresh",
        refresh_payload,
        timeout=args.timeout_sec,
    )

    image_assets = refresh_resp.get("image_assets") or {}
    assets = image_assets.get("assets") or []
    name_map = _manifest_name_map(outputs)

    failures: list[str] = []

    provider = str(image_assets.get("provider") or "")
    status = str(image_assets.get("status") or "")
    reason = str(image_assets.get("reason") or "")
    fallback = image_assets.get("fallback") or {}
    fallback_to = str(fallback.get("to_provider") or "")

    print("image_assets.provider =", provider)
    print("image_assets.status =", status)
    print("image_assets.reason =", reason)
    print("image_assets.asset_count =", image_assets.get("asset_count"))
    print("image_assets.fallback =", fallback)

    if provider != "api_image_generator":
        failures.append(f"provider is not api_image_generator: {provider}")

    if fallback_to == "pillow_storybook_renderer":
        failures.append("fallback_to pillow_storybook_renderer is not allowed")

    if status in {"pending", "retrying", "failed"}:
        failures.append(f"image_assets status is not ready: {status}; reason={reason}")

    if not assets:
        failures.append("image_assets.assets is empty")

    for asset in assets:
        scene_id = str(asset.get("scene_id") or asset.get("shot_id") or "unknown")
        prompt = str(asset.get("prompt") or "")
        selected_asset_ref = asset.get("selected_asset_ref") or {}
        candidate_asset_refs = asset.get("candidate_asset_refs") or []
        required_names = _required_names_from_asset(asset, name_map)

        print(f"scene={scene_id} required_names={required_names} candidate_count={len(candidate_asset_refs)}")

        if not selected_asset_ref:
            failures.append(f"{scene_id}: selected_asset_ref is empty")

        if not candidate_asset_refs:
            failures.append(f"{scene_id}: candidate_asset_refs is empty")

        if len(required_names) >= 2:
            if "required scene characters:" not in prompt:
                failures.append(f"{scene_id}: missing required scene characters block")

            if "scene cast lock:" not in prompt:
                failures.append(f"{scene_id}: missing scene cast lock block")

            if ("must all be clearly visible" not in prompt) and ("include all of" not in prompt):
                failures.append(f"{scene_id}: missing visibility hard rule")

            for name in required_names:
                if name not in prompt:
                    failures.append(f"{scene_id}: prompt missing required character name: {name}")

    if failures:
        print("SUMMARY = FAIL")
        for item in failures:
            print("-", item)
        return 1

    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
