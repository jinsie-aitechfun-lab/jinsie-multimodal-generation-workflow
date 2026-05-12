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
    parser = argparse.ArgumentParser(description="Monitor multi-character refresh flow.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--topic", default="小兔子和小乌龟赛跑")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--timeout-sec", type=int, default=240)
    args = parser.parse_args()

    workflow_id = f"monitor_multi_char_{int(time.time() * 1000)}"
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

    print("===== STEP 1: POST /v1/workflow/run =====")
    run_resp = _post_json(f"{args.base_url.rstrip('/')}/v1/workflow/run", run_payload, timeout=120)
    print(json.dumps(run_resp, ensure_ascii=False, indent=2))

    print("\n===== STEP 2: WAIT outputs.json =====")
    outputs_path = _wait_for_outputs(workflow_id, timeout_sec=args.timeout_sec)
    print("outputs_path =", outputs_path)

    data = json.loads(outputs_path.read_text(encoding="utf-8"))
    outputs = data.get("outputs") or {}

    name_map = _manifest_name_map(outputs)
    storyboard = outputs.get("storyboard") or {}
    scenes = storyboard.get("scenes") or []

    print("\n===== STEP 3: outputs summary =====")
    print("workflow_id =", data.get("workflow_id"))
    print("run_id =", data.get("run_id"))
    print("status =", data.get("status"))
    print("output_keys =", list(outputs.keys()))
    print("manifest_name_map =", name_map)
    print("scene_count =", len(scenes))

    for scene in scenes:
        scene_id = str(scene.get("scene_id") or "")
        bindings = scene.get("characters") or []
        names = []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            cid = str(binding.get("character_id") or "").strip()
            if cid and cid in name_map:
                names.append(name_map[cid])
        print(f"scene={scene_id} scene_characters={names}")

    image_review = outputs.get("image_review") or {}

    refresh_payload = {
        "workflow_id": data.get("workflow_id"),
        "session_id": data.get("session_id"),
        "run_id": data.get("run_id"),
        "storyboard": storyboard,
        "workflow_input": run_payload["input"],
        "image_review": image_review,
        "video_provider": run_payload["input"].get("video_provider", "mock"),
    }

    print("\n===== STEP 4: POST /v1/image-review/refresh =====")
    refresh_resp = _post_json(
        f"{args.base_url.rstrip('/')}/v1/image-review/refresh",
        refresh_payload,
        timeout=args.timeout_sec,
    )

    save_path = Path("assets/mock") / workflow_id / "refresh_response.json"
    save_path.write_text(json.dumps(refresh_resp, ensure_ascii=False, indent=2), encoding="utf-8")
    print("refresh_response_path =", save_path)

    image_assets = refresh_resp.get("image_assets") or {}
    assets = image_assets.get("assets") or []

    print("\n===== STEP 5: refresh summary =====")
    print("image_assets.provider =", image_assets.get("provider"))
    print("image_assets.status =", image_assets.get("status"))
    print("image_assets.reason =", image_assets.get("reason"))
    print("image_assets.detail =", image_assets.get("detail"))
    print("image_assets.asset_count =", image_assets.get("asset_count"))
    print("image_assets.fallback =", image_assets.get("fallback"))
    print("image_assets.character_anchor =", image_assets.get("character_anchor"))

    if not assets:
        print("\nNO ASSETS GENERATED")
        return 1

    for index, asset in enumerate(assets, start=1):
        scene_id = str(asset.get("scene_id") or asset.get("shot_id") or f"item_{index}")
        required_names = _required_names_from_asset(asset, name_map)
        prompt = str(asset.get("prompt") or "")
        selected_asset_ref = asset.get("selected_asset_ref") or {}
        candidate_asset_refs = asset.get("candidate_asset_refs") or []
        prompt_has_all_names = all(name in prompt for name in required_names) if required_names else True
        has_required_block = "required scene characters:" in prompt
        has_scene_cast_lock = "scene cast lock:" in prompt
        has_visibility_rule = ("must all be clearly visible" in prompt) or ("include all of" in prompt)

        print("\n----- ASSET -----")
        print("scene_id =", scene_id)
        print("required_names =", required_names)
        print("prompt_has_all_names =", prompt_has_all_names)
        print("has_required_block =", has_required_block)
        print("has_scene_cast_lock =", has_scene_cast_lock)
        print("has_visibility_rule =", has_visibility_rule)
        print("candidate_count =", len(candidate_asset_refs))
        print("selected_asset_ref.file_name =", selected_asset_ref.get("file_name"))
        print("selected_asset_ref.relative_path =", selected_asset_ref.get("relative_path"))
        print("selected_asset_ref.public_url =", selected_asset_ref.get("public_url"))
        print("selected_asset_ref.reference_image_support =", selected_asset_ref.get("reference_image_support"))
        print("prompt_preview =", prompt[:1200])

    print("\nSUMMARY = DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
