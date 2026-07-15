"""Contract verification for runner refactor Step 19.

Verifies RunnerImageReviewSupport owns single-scene image-review refresh
orchestration while WorkflowRunner delegates through a thin wrapper. This is
an in-process verification and does not call real image generation services.

Usage:
    python scripts/verify_step19_image_review_refresh_scene.py
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
    "characters": [
        {
            "character_id": "char_primary_01",
            "display_name": "小兔子",
            "role_type": "primary",
        }
    ],
}

ASSET_REF = {
    "scene_id": "scene_01",
    "file_name": "scene_01__candidate_a.png",
    "relative_path": "assets/mock/image/run_verify/scene_01__candidate_a.png",
    "public_url": "/assets/mock/image/run_verify/scene_01__candidate_a.png",
    "mime_type": "image/png",
    "provider": "pillow_storybook_renderer",
}


def make_generated_single_scene_assets() -> dict:
    return {
        "enabled": True,
        "run_id": "run_verify_step19",
        "provider": "pillow_storybook_renderer",
        "asset_count": 1,
        "assets": [
            {
                "scene_id": "scene_01",
                "scene_title": "一起过河",
                "characters": SCENE["characters"],
                "character_ids": ["char_primary_01"],
                "prompt": "storybook prompt",
                "selected_asset_ref": dict(ASSET_REF),
                "file_name": ASSET_REF["file_name"],
                "relative_path": ASSET_REF["relative_path"],
                "public_url": ASSET_REF["public_url"],
                "mime_type": ASSET_REF["mime_type"],
                "status": "generated",
                "candidate_asset_refs": [dict(ASSET_REF)],
                "selection_source": "auto_filter",
                "selection_reason": "selected by fake adapter",
                "candidate_scores": [],
            }
        ],
    }


def make_pending_single_scene_assets() -> dict:
    return {
        "enabled": False,
        "run_id": "run_verify_step19",
        "provider": "api_image_generator",
        "status": "retrying",
        "reason": "rate_limited",
        "asset_count": 0,
        "assets": [],
        "candidate_scores": [],
    }


def make_empty_image_review() -> dict:
    return {
        "enabled": True,
        "mode": "selection_contract",
        "provider": "pillow_storybook_renderer",
        "selected_count": 0,
        "selected_assets": [],
    }


def refresh_kwargs() -> dict:
    return {
        "workflow_id": "wf_verify_step19",
        "session_id": "sess_verify_step19",
        "run_id": "run_verify_step19",
        "scene_id": "scene_01",
        "storyboard": {"scenes": [SCENE]},
        "workflow_input": {
            "topic": "写一个关于小兔子和小乌龟过河的故事",
            "duration_sec": 60,
            "video_provider": "mock",
        },
        "image_review": make_empty_image_review(),
        "character_manifest": {
            "characters": [
                {
                    "character_id": "char_primary_01",
                    "display_name": "小兔子",
                    "role_type": "primary",
                }
            ]
        },
        "image_prompts": {
            "prompts": [
                {
                    "scene_id": "scene_01",
                    "prompt": "storybook prompt",
                    "characters": SCENE["characters"],
                }
            ]
        },
        "video_provider": "mock",
    }


def main() -> int:
    runner = WorkflowRunner()

    captured = {}

    def fake_run_single_scene_image_asset(
        *, ctx, outputs, scene, scene_index, preserve_seed=False
    ):
        del preserve_seed
        captured["ctx"] = ctx
        captured["outputs"] = outputs
        captured["scene"] = scene
        captured["scene_index"] = scene_index
        return make_generated_single_scene_assets()

    runner._run_single_scene_image_asset = fake_run_single_scene_image_asset

    result = runner.refresh_image_review_scene(**refresh_kwargs())
    direct_result = runner._image_review.refresh_image_review_scene(**refresh_kwargs())
    assert result == direct_result

    assert captured["ctx"].workflow_id == "wf_verify_step19"
    assert captured["ctx"].session_id == "sess_verify_step19"
    assert captured["ctx"].run_id == "run_verify_step19"
    assert captured["ctx"].input.video_provider == "mock"
    assert captured["scene"] == SCENE
    assert captured["scene_index"] == 1
    assert captured["outputs"]["character_manifest"]["characters"][0][
        "display_name"
    ] == "小兔子"
    assert captured["outputs"]["image_prompts"]["prompts"][0]["scene_id"] == "scene_01"

    assert result["scene_id"] == "scene_01"
    assert result["scene_image_asset"]["provider"] == "pillow_storybook_renderer"
    assert result["scene_review_item"]["selected_asset_ref"] == ASSET_REF
    assert result["image_review"]["selected_count"] == 1
    assert result["image_assets"]["asset_count"] == 1
    assert result["image_assets"]["assets"][0]["selected_asset_ref"] == ASSET_REF
    assert isinstance(result["video_prompts"].get("prompts"), list)

    def fake_pending_single_scene_image_asset(
        *, ctx, outputs, scene, scene_index, preserve_seed=False
    ):
        del preserve_seed
        return make_pending_single_scene_assets()

    runner._run_single_scene_image_asset = fake_pending_single_scene_image_asset
    pending_result = runner.refresh_image_review_scene(**refresh_kwargs())
    assert pending_result["scene_image_asset"]["status"] == "retrying"
    assert pending_result["scene_review_item"] == {}
    assert pending_result["image_review"] == make_empty_image_review()

    try:
        bad_kwargs = refresh_kwargs()
        bad_kwargs["scene_id"] = "scene_missing"
        runner.refresh_image_review_scene(**bad_kwargs)
    except ValueError as error:
        assert "scene_id not found" in str(error)
    else:
        raise AssertionError("missing scene_id should raise ValueError")

    print("[OK] refresh-scene generated asset contract")
    print("[OK] refresh-scene pending asset contract")
    print("[OK] refresh-scene runner proxy contract")
    print("PASS: Step 19 image review refresh-scene support contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
