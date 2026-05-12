from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

DEFAULT_BASE_URL = "http://127.0.0.1:8004"
DEFAULT_TOPIC = "小兔子和小乌龟赛跑"


def post_workflow(base_url: str, workflow_id: str, topic: str, duration_sec: int) -> dict[str, Any]:
    payload = {
        "workflow_id": workflow_id,
        "session_id": f"{workflow_id}_session",
        "steps": [
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "sentence_shots"},
            {"name": "image_prompts"},
            {"name": "image_assets"},
        ],
        "input": {
            "topic": topic,
            "duration_sec": duration_sec,
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

    req = urllib_request.Request(
        url=f"{base_url.rstrip('/')}/v1/workflow/run",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=60) as resp:
        raw = resp.read()

    return json.loads(raw.decode("utf-8"))


def wait_for_outputs(workflow_id: str, timeout_sec: int) -> Path:
    path = Path("assets/mock") / workflow_id / "outputs.json"
    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        if path.exists():
            return path
        time.sleep(2)

    raise TimeoutError(f"outputs.json not ready: {path}")


def manifest_name_map(outputs: dict[str, Any]) -> dict[str, str]:
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


def required_names_from_asset(asset: dict[str, Any], name_map: dict[str, str]) -> list[str]:
    result: list[str] = []

    for binding in asset.get("characters") or []:
        if not isinstance(binding, dict):
            continue
        character_id = str(binding.get("character_id") or "").strip()
        name = name_map.get(character_id)
        if name and name not in result:
            result.append(name)

    return result


def validate_outputs(data: dict[str, Any]) -> tuple[bool, list[str]]:
    outputs = data.get("outputs") or {}
    image_assets = outputs.get("image_assets") or {}
    assets = image_assets.get("assets") or []
    provider = str(image_assets.get("provider") or "")
    fallback = image_assets.get("fallback") or {}
    fallback_to = str(fallback.get("to_provider") or "")
    name_map = manifest_name_map(outputs)

    failures: list[str] = []

    if provider != "api_image_generator":
        failures.append(f"image_assets.provider is not api_image_generator: {provider}")

    if fallback_to == "pillow_storybook_renderer":
        failures.append("image_assets fallback_to pillow_storybook_renderer is not allowed")

    if not assets:
        failures.append("image_assets.assets is empty")
        return False, failures

    for asset in assets:
        scene_id = str(asset.get("scene_id") or asset.get("shot_id") or "unknown")
        prompt = str(asset.get("prompt") or "")
        required_names = required_names_from_asset(asset, name_map)

        if len(required_names) >= 2:
            if "required scene characters:" not in prompt:
                failures.append(f"{scene_id}: prompt missing 'required scene characters:' block")

            for name in required_names:
                if name not in prompt:
                    failures.append(f"{scene_id}: prompt missing required character name: {name}")

            if "must all be clearly visible" not in prompt and "include all of" not in prompt:
                failures.append(f"{scene_id}: prompt missing hard multi-character visibility rule")

        print(
            f"scene={scene_id} provider={provider} required={required_names} prompt_ok={'yes' if not [n for n in required_names if n not in prompt] else 'no'}"
        )

    return len(failures) == 0, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Acceptance checks for scene character presence.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--timeout-sec", type=int, default=180)
    args = parser.parse_args()

    workflow_id = f"acceptance_scene_presence_{int(time.time() * 1000)}"
    print(f"workflow_id = {workflow_id}")
    print(f"topic = {args.topic}")

    response = post_workflow(
        base_url=args.base_url,
        workflow_id=workflow_id,
        topic=args.topic,
        duration_sec=args.duration,
    )
    print("run_response =", json.dumps(response, ensure_ascii=False))

    path = wait_for_outputs(workflow_id, args.timeout_sec)
    print("outputs_path =", path)

    data = json.loads(path.read_text(encoding="utf-8"))
    ok, failures = validate_outputs(data)

    if ok:
        print("SUMMARY = PASS")
        return 0

    print("SUMMARY = FAIL")
    for item in failures:
        print("-", item)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
