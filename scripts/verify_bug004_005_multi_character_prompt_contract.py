from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


def build_request() -> WorkflowRunRequest:
    return WorkflowRunRequest(
        workflow_id="verify_bug004_005_multi_character_prompt_contract",
        session_id="verify_bug004_005_multi_character_prompt_contract",
        steps=[
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "image_prompts"},
        ],
        input={
            "topic": "写一个关于兔子和乌龟赛跑的故事",
            "duration_sec": 60,
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
        },
    )


def main() -> int:
    os.environ["CHARACTER_PROFILE_PROVIDER"] = "template"

    result = WorkflowRunner().run(build_request())
    manifest = result.outputs.get("character_manifest") or {}
    storyboard = result.outputs.get("storyboard") or {}
    image_prompts = result.outputs.get("image_prompts") or {}

    characters = manifest.get("characters") or []
    scenes = storyboard.get("scenes") or []
    prompts = image_prompts.get("prompts") or []
    failures: list[str] = []

    print("manifest_count =", len(characters))
    print("scene_count =", len(scenes))
    print("prompt_count =", len(prompts))

    names = [
        str(item.get("display_name") or item.get("species") or "").strip()
        for item in characters
        if str(item.get("display_name") or item.get("species") or "").strip()
    ]
    print("manifest_names =", names)

    if len(characters) < 2:
        failures.append("character_manifest must contain at least two characters")
    for expected_name in ["兔子", "乌龟"]:
        if not any(expected_name in name for name in names):
            failures.append(f"character_manifest missing {expected_name}")

    for index, scene in enumerate(scenes, start=1):
        scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
        scene_characters = scene.get("characters") or []
        scene_names = [
            str(item.get("display_name") or item.get("species") or "").strip()
            for item in scene_characters
            if isinstance(item, dict)
        ]
        print(f"{scene_id}_characters =", scene_names)

        for expected_name in ["兔子", "乌龟"]:
            if not any(expected_name in name for name in scene_names):
                failures.append(f"{scene_id}: missing scene character {expected_name}")

    for index, item in enumerate(prompts, start=1):
        scene_id = str(item.get("scene_id") or f"prompt_{index:02d}")
        prompt = str(item.get("prompt") or "")
        required_names = item.get("required_character_names") or []
        required_ids = item.get("required_character_ids") or []

        print("---")
        print("scene_id =", scene_id)
        print("required_character_names =", required_names)
        print("required_character_ids =", required_ids)
        print("has_scene_cast_lock =", "scene cast lock" in prompt)
        print("has_cross_character_avoid =", "cross-character must avoid" in prompt)

        if "scene cast lock" not in prompt:
            failures.append(f"{scene_id}: prompt missing scene cast lock")
        if "required scene characters" not in prompt:
            failures.append(f"{scene_id}: prompt missing required scene characters")
        if "cross-character must avoid" not in prompt:
            failures.append(f"{scene_id}: prompt missing cross-character constraints")
        for expected in ["兔子", "乌龟", "no turtle shell", "no rabbit ears"]:
            if expected not in prompt:
                failures.append(f"{scene_id}: prompt missing {expected}")
        for expected_name in ["兔子", "乌龟"]:
            if not any(expected_name in str(name) for name in required_names):
                failures.append(
                    f"{scene_id}: required_character_names missing {expected_name}"
                )
        if len(required_ids) < 2:
            failures.append(f"{scene_id}: required_character_ids missing characters")

    if failures:
        print("---")
        print("SUMMARY = FAIL")
        for failure in failures:
            print("-", failure)
        return 1

    print("---")
    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
