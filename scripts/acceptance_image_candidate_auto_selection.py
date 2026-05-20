from __future__ import annotations

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
        failures.append("image_assets.assets is empty")

    for index, item in enumerate(assets, start=1):
        scene_id = str(item.get("scene_id") or item.get("shot_id") or f"item_{index}")
        selected_asset_ref = item.get("selected_asset_ref") or {}
        candidate_asset_refs = item.get("candidate_asset_refs") or []
        candidate_scores = item.get("candidate_scores") or []

        print("---")
        print("scene_id =", scene_id)
        print("selection_source =", item.get("selection_source"))
        print("selection_reason =", item.get("selection_reason"))
        print("selected_file =", selected_asset_ref.get("file_name"))
        print("candidate_count =", len(candidate_asset_refs))
        print("candidate_scores_count =", len(candidate_scores))

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
