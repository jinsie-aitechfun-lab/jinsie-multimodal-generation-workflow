"""Contract verification for runner refactor Step 18.

Verifies RunnerImageReviewSupport owns manual image-review selection updates
and WorkflowRunner delegates through thin wrappers. This is an in-process
verification and does not require the API server.

Usage:
    python scripts/verify_step18_image_review_selection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.runner import WorkflowRunner


SCENE = {
    "scene_id": "scene_01",
    "scene_title": "一起过河",
    "visual_description": "小兔子和小乌龟站在河边。",
    "narration": "两个朋友来到河边。",
    "duration_sec": 10,
}

ORIGINAL_REF = {
    "scene_id": "scene_01",
    "file_name": "scene_01__candidate_a.png",
    "relative_path": "assets/mock/image/run_verify/scene_01__candidate_a.png",
    "public_url": "/assets/mock/image/run_verify/scene_01__candidate_a.png",
    "mime_type": "image/png",
    "provider": "pillow_storybook_renderer",
}

SELECTED_REF = {
    "scene_id": "scene_01",
    "file_name": "scene_01__candidate_b.png",
    "relative_path": "assets/mock/image/run_verify/scene_01__candidate_b.png",
    "public_url": "/assets/mock/image/run_verify/scene_01__candidate_b.png",
    "mime_type": "image/png",
    "provider": "pillow_storybook_renderer",
}


def make_image_review() -> dict:
    return {
        "enabled": True,
        "mode": "selection_contract",
        "provider": "pillow_storybook_renderer",
        "selected_count": 1,
        "selected_assets": [
            {
                "scene_id": "scene_01",
                "scene_title": "一起过河",
                "review_status": "auto_selected",
                "selection_mode": "default_first_pass",
                "selection_source": "default_auto_selection",
                "selection_reason": "default_selected_from_image_assets",
                "selected_asset_ref": dict(ORIGINAL_REF),
                "candidate_asset_refs": [dict(ORIGINAL_REF)],
                "candidate_scores": [],
                "characters": [],
                "character_ids": [],
                "prompt": "storybook prompt",
            }
        ],
    }


def main() -> int:
    runner = WorkflowRunner()
    support = runner._image_review

    updated = runner._apply_manual_image_selection(
        image_review=make_image_review(),
        scene_id="scene_01",
        selected_asset_ref=SELECTED_REF,
    )
    direct = support.apply_manual_image_selection(
        image_review=make_image_review(),
        scene_id="scene_01",
        selected_asset_ref=SELECTED_REF,
    )
    assert updated == direct

    item = updated["selected_assets"][0]
    assert item["selected_asset_ref"] == SELECTED_REF
    assert item["selection_source"] == "manual_selection"
    assert item["selection_mode"] == "manual_click_override"
    assert item["review_status"] == "manually_selected"
    assert item["selection_reason"] == "selected_by_user_click"
    assert item["candidate_asset_refs"] == [ORIGINAL_REF, SELECTED_REF]
    assert updated["selected_count"] == 1
    assert updated["mode"] == "selection_contract"

    repeated = runner._apply_manual_image_selection(
        image_review=updated,
        scene_id="scene_01",
        selected_asset_ref=SELECTED_REF,
    )
    assert repeated["selected_assets"][0]["candidate_asset_refs"] == [
        ORIGINAL_REF,
        SELECTED_REF,
    ]

    try:
        runner._apply_manual_image_selection(
            image_review=make_image_review(),
            scene_id="scene_missing",
            selected_asset_ref=SELECTED_REF,
        )
    except ValueError as error:
        assert "scene_id not found" in str(error)
    else:
        raise AssertionError("missing scene_id should raise ValueError")

    result = runner.update_image_review_selection(
        workflow_id="wf_verify_step18",
        session_id="sess_verify_step18",
        run_id="run_verify_step18",
        scene_id="scene_01",
        selected_asset_ref=SELECTED_REF,
        image_review=make_image_review(),
        storyboard={"scenes": [SCENE]},
        workflow_input={
            "topic": "写一个关于小兔子和小乌龟过河的故事",
            "duration_sec": 60,
            "video_provider": "mock",
        },
        video_provider="mock",
    )
    direct_result = support.update_image_review_selection(
        workflow_id="wf_verify_step18",
        session_id="sess_verify_step18",
        run_id="run_verify_step18",
        scene_id="scene_01",
        selected_asset_ref=SELECTED_REF,
        image_review=make_image_review(),
        storyboard={"scenes": [SCENE]},
        workflow_input={
            "topic": "写一个关于小兔子和小乌龟过河的故事",
            "duration_sec": 60,
            "video_provider": "mock",
        },
        video_provider="mock",
    )
    assert result == direct_result
    assert result["image_review"]["selected_assets"][0]["selected_asset_ref"] == (
        SELECTED_REF
    )
    assert result["image_assets"]["asset_count"] == 1
    assert result["image_assets"]["assets"][0]["selected_asset_ref"] == SELECTED_REF
    assert "video_prompts" in result
    assert isinstance(result["video_prompts"].get("prompts"), list)

    print("[OK] manual image selection payload contract")
    print("[OK] manual image selection duplicate candidate contract")
    print("[OK] update image review selection proxy contract")
    print("PASS: Step 18 image review selection support contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
