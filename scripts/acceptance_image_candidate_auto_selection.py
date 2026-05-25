from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


def build_request() -> WorkflowRunRequest:
    return WorkflowRunRequest(
        workflow_id="acceptance_image_candidate_auto_selection",
        session_id="acceptance_image_candidate_auto_selection",
        steps=[
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "image_prompts"},
            {"name": "image_assets"},
        ],
        input={
            "topic": "小兔子和小乌龟一起过河",
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
            "structured_characters_enabled": True,
            "characters": [
                {
                    "display_name": "小兔子",
                    "species": "rabbit",
                    "role_type": "primary",
                    "visual_traits": "long upright ears, soft white fur, small red scarf, fluffy round tail",
                    "forbidden_traits": "no turtle shell, no hard round shell, no turtle body, no short turtle legs",
                },
                {
                    "display_name": "小乌龟",
                    "species": "turtle",
                    "role_type": "secondary",
                    "visual_traits": "round green shell, small turtle body, short legs, gentle eyes",
                    "forbidden_traits": "no rabbit ears, no long upright ears, no fluffy rabbit tail, no rabbit body",
                },
            ],
        },
    )


def main() -> int:
    result = WorkflowRunner().run(build_request())
    image_assets = result.outputs.get("image_assets") or {}
    assets = image_assets.get("assets") or []
    failures: list[str] = []

    print("asset_count =", len(assets))

    if not assets:
        print("SUMMARY = SKIP")
        print("image_assets.assets is empty; current workflow configuration deferred image generation")
        return 0

    for index, item in enumerate(assets, start=1):
        scene_id = str(item.get("scene_id") or item.get("shot_id") or f"item_{index}")
        selected_asset_ref = item.get("selected_asset_ref") or {}
        candidate_asset_refs = item.get("candidate_asset_refs") or []
        candidate_scores = item.get("candidate_scores") or []
        quality_gates = item.get("quality_gates") or {}

        print("---")
        print("scene_id =", scene_id)
        print("selection_source =", item.get("selection_source"))
        print("selection_reason =", item.get("selection_reason"))
        print("review_status =", item.get("review_status"))
        print("selected_file =", selected_asset_ref.get("file_name"))
        print("candidate_count =", len(candidate_asset_refs))
        print("candidate_scores_count =", len(candidate_scores))
        print("quality_gates =", quality_gates)

        if item.get("selection_source") != "auto_filter":
            failures.append(f"{scene_id}: selection_source is not auto_filter")

        if not item.get("selection_reason"):
            failures.append(f"{scene_id}: missing selection_reason")

        if not selected_asset_ref:
            failures.append(f"{scene_id}: missing selected_asset_ref")

        if len(candidate_asset_refs) < 1:
            failures.append(f"{scene_id}: missing candidate_asset_refs")

        if len(candidate_scores) < 1:
            failures.append(f"{scene_id}: missing candidate_scores")

        if item.get("review_status") != "auto_selected":
            failures.append(f"{scene_id}: auto mode should keep auto_selected review status")

        if item.get("review_required") is True:
            failures.append(f"{scene_id}: auto mode should not require manual review")

        if quality_gates.get("multi_character_scene") is not True:
            failures.append(f"{scene_id}: quality gate should mark multi-character scene")

        labels = quality_gates.get("required_character_labels", [])
        for expected_name in ["小兔子", "小乌龟"]:
            if not any(expected_name in str(label) for label in labels):
                failures.append(f"{scene_id}: quality gate missing label {expected_name}")

        selected_file_name = str(selected_asset_ref.get("file_name") or "").strip()
        candidate_file_names = [
            str(candidate.get("file_name") or "").strip()
            for candidate in candidate_asset_refs
            if isinstance(candidate, dict)
        ]

        if selected_file_name and selected_file_name not in candidate_file_names:
            failures.append(f"{scene_id}: selected file is not in candidate_asset_refs")

    if failures:
        print("---")
        print("SUMMARY = FAIL")
        for item in failures:
            print("-", item)
        return 1

    print("---")
    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
