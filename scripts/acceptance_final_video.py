from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from PIL import Image, ImageDraw


DEFAULT_BASE_URL = "http://127.0.0.1:8004"


def post_json(base_url: str, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    req = urllib_request.Request(
        url=f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()

    return json.loads(raw.decode("utf-8"))


def build_workflow_input(duration_sec: int) -> dict[str, Any]:
    return {
        "topic": "小汽车去旅行",
        "duration_sec": duration_sec,
        "audience": "children",
        "tone": "warm",
        "visual_style": "storybook",
        "character_style": "animal",
        "language": "zh",
        "audio_enabled": False,
        "voiceover_enabled": False,
        "subtitle_enabled": True,
        "video_provider": "mock",
        "output_mode": "full_video",
    }


def create_placeholder_image(path: Path, scene_index: int, scene_title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (720, 1280), color=(245, 247, 250))
    draw = ImageDraw.Draw(image)

    draw.rectangle((40, 40, 680, 1240), outline=(180, 190, 205), width=4)
    draw.text((80, 120), f"Scene {scene_index:02d}", fill=(30, 41, 59))
    draw.text((80, 180), scene_title[:24], fill=(30, 41, 59))
    draw.text((80, 1120), "Final Video Acceptance", fill=(71, 85, 105))

    image.save(path)


def build_local_image_assets(run_id: str, storyboard: dict[str, Any]) -> dict[str, Any]:
    scenes = storyboard.get("scenes") or []
    image_dir = Path("assets/mock/image") / run_id
    assets: list[dict[str, Any]] = []

    for index, scene in enumerate(scenes, start=1):
        scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
        scene_title = str(scene.get("scene_title") or f"Scene {index:02d}")
        duration_sec = float(scene.get("duration_sec") or 3.0)

        file_name = f"{scene_id}__acceptance.png"
        relative_path = image_dir / file_name

        create_placeholder_image(relative_path, index, scene_title)

        asset_ref = {
            "scene_id": scene_id,
            "file_name": file_name,
            "relative_path": str(relative_path),
            "public_url": f"/assets/mock/image/{run_id}/{file_name}",
            "mime_type": "image/png",
            "provider": "acceptance_placeholder",
            "duration_sec": duration_sec,
            "duration_estimate_sec": None,
        }

        assets.append(
            {
                "scene_id": scene_id,
                "scene_title": scene_title,
                "characters": scene.get("characters") or [],
                "character_ids": scene.get("character_ids") or [],
                "prompt": str(scene.get("visual_description") or scene_title),
                "selected_asset_ref": asset_ref,
                "file_name": file_name,
                "relative_path": str(relative_path),
                "public_url": asset_ref["public_url"],
                "mime_type": "image/png",
                "duration_sec": duration_sec,
                "duration_estimate_sec": None,
                "status": "generated",
                "candidate_asset_refs": [asset_ref],
            }
        )

    return {
        "enabled": True,
        "run_id": run_id,
        "provider": "acceptance_placeholder",
        "asset_count": len(assets),
        "assets": assets,
    }


def run_acceptance(base_url: str, duration_sec: int, timeout: float) -> int:
    workflow_id = f"acceptance_final_video_{duration_sec}s"
    session_id = f"acceptance_final_video_{duration_sec}s_{int(time.time())}"
    workflow_input = build_workflow_input(duration_sec)

    print("Final video acceptance")
    print(f"base_url = {base_url}")
    print(f"duration_sec = {duration_sec}")

    run_payload = {
        "workflow_id": workflow_id,
        "session_id": session_id,
        "steps": [
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "dialogue_script"},
            {"name": "audio_segments"},
            {"name": "narration"},
            {"name": "subtitles"},
            {"name": "render_plan"},
        ],
        "input": workflow_input,
    }

    run_data = post_json(base_url, "/v1/workflow/run", run_payload, timeout)
    outputs = run_data.get("outputs") or {}
    storyboard = outputs.get("storyboard") or {}
    run_id = str(run_data.get("run_id") or f"run_acceptance_{int(time.time())}")

    print("workflow.status =", run_data.get("status"))
    print("run_id =", run_id)

    image_assets = build_local_image_assets(run_id, storyboard)
    print("asset_count =", image_assets.get("asset_count"))

    render_payload = {
        "workflow_id": run_data.get("workflow_id"),
        "session_id": run_data.get("session_id"),
        "run_id": run_id,
        "workflow_input": workflow_input,
        "image_assets": image_assets,
        "audio_segments": outputs.get("audio_segments") or {},
        "subtitles": outputs.get("subtitles") or {},
    }

    render_data = post_json(base_url, "/v1/final-video/render", render_payload, timeout)
    final_video = render_data.get("final_video") or {}

    actual_duration = final_video.get("actual_duration_sec")
    declared_duration = final_video.get("duration_sec")
    base_duration = final_video.get("base_video_duration_sec")
    relative_path = final_video.get("relative_path")

    print("final_video.status =", final_video.get("status"))
    print("duration_sec =", declared_duration)
    print("actual_duration_sec =", actual_duration)
    print("base_video_duration_sec =", base_duration)
    print("audio_mode =", final_video.get("audio_mode"))
    print("relative_path =", relative_path)

    failures: list[str] = []

    if final_video.get("status") != "generated":
        failures.append("final_video.status is not generated")

    if not isinstance(actual_duration, (int, float)) or actual_duration <= 0:
        failures.append("actual_duration_sec missing or invalid")

    if not isinstance(base_duration, (int, float)) or base_duration <= 0:
        failures.append("base_video_duration_sec missing or invalid")

    if isinstance(actual_duration, (int, float)):
        tolerance = 1.5
        if abs(float(actual_duration) - duration_sec) > tolerance:
            failures.append(
                f"actual_duration_sec out of tolerance: {actual_duration}, target={duration_sec}"
            )

    if not relative_path:
        failures.append("relative_path missing")
    else:
        video_path = Path(str(relative_path))
        if not video_path.exists():
            failures.append(f"final video file missing: {relative_path}")
        elif video_path.stat().st_size <= 0:
            failures.append(f"final video file is empty: {relative_path}")
        else:
            print("file_exists = True")
            print("file_size =", video_path.stat().st_size)

    if failures:
        print("\nFAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nPASS")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Acceptance check for final video rendering.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--duration-sec", type=int, default=60)
    parser.add_argument("--timeout", type=float, default=180.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        return run_acceptance(args.base_url, args.duration_sec, args.timeout)
    except urllib_error.URLError as error:
        print(f"FAIL request_error: {error}")
        return 1
    except Exception as error:
        print(f"FAIL unexpected_error: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
