"""Contract verification for image-review refresh payload handoff.

Verifies /v1/image-review/refresh can pass character_manifest and image_prompts
through WorkflowRunner.refresh_image_review without real image generation.

Usage:
    python scripts/verify_bug003_image_review_refresh_contract.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import ImageReviewRefreshRequest
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
    "relative_path": "assets/mock/image/run_verify_bug003/scene_01__candidate_a.png",
    "public_url": "/assets/mock/image/run_verify_bug003/scene_01__candidate_a.png",
    "mime_type": "image/png",
    "provider": "pillow_storybook_renderer",
}

EXPLICIT_CHARACTER_MANIFEST = {
    "characters": [
        {
            "character_id": "char_primary_01",
            "display_name": "小兔子",
            "role_type": "primary",
        }
    ]
}

STORED_CHARACTER_MANIFEST = {
    "characters": [
        {
            "character_id": "char_old",
            "display_name": "旧角色",
            "role_type": "primary",
        }
    ]
}

PROMPT_ITEM = {
    "scene_id": "scene_01",
    "prompt": "explicit storybook prompt",
    "characters": SCENE["characters"],
}

STORED_IMAGE_PROMPTS = {
    "prompts": [
        {
            "scene_id": "scene_01",
            "prompt": "stored storybook prompt",
        }
    ]
}


def make_workflow_input() -> dict:
    return {
        "topic": "写一个关于小兔子和小乌龟过河的故事",
        "duration_sec": 60,
        "video_provider": "mock",
    }


def make_image_review() -> dict:
    return {
        "enabled": True,
        "mode": "selection_contract",
        "provider": "pillow_storybook_renderer",
        "selected_count": 0,
        "selected_assets": [],
    }


def make_generated_assets(run_id: str) -> dict:
    return {
        "enabled": True,
        "run_id": run_id,
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


def save_stored_context(runner: WorkflowRunner, run_id: str) -> None:
    runner._session.save_run_context(
        workflow_id="wf_stored_bug003",
        session_id="sess_stored_bug003",
        run_id=run_id,
        outputs={
            "storyboard": {"scenes": [SCENE]},
            "character_manifest": STORED_CHARACTER_MANIFEST,
            "image_prompts": STORED_IMAGE_PROMPTS,
            "image_review": make_image_review(),
        },
        workflow_input=make_workflow_input(),
    )


def run_refresh(runner: WorkflowRunner, run_id: str, **overrides) -> tuple[dict, dict]:
    captured = {}

    def fake_run_image_assets(ctx, outputs):
        captured["ctx"] = ctx
        captured["outputs"] = outputs
        return make_generated_assets(run_id)

    runner._run_image_assets = fake_run_image_assets
    result = runner.refresh_image_review(
        workflow_id="wf_request_bug003",
        session_id=None,
        run_id=run_id,
        storyboard=overrides.pop("storyboard", {"scenes": [SCENE]}),
        workflow_input=overrides.pop("workflow_input", make_workflow_input()),
        image_review=overrides.pop("image_review", make_image_review()),
        video_provider="mock",
        **overrides,
    )
    return result, captured


def verify_explicit_payload_wins() -> None:
    runner = WorkflowRunner()
    run_id = "run_verify_bug003_explicit"
    save_stored_context(runner, run_id)

    result, captured = run_refresh(
        runner,
        run_id,
        character_manifest=EXPLICIT_CHARACTER_MANIFEST,
        image_prompts=[PROMPT_ITEM],
    )

    outputs = captured["outputs"]
    assert captured["ctx"].session_id == "sess_stored_bug003"
    assert outputs["character_manifest"] == EXPLICIT_CHARACTER_MANIFEST
    assert outputs["image_prompts"] == {"prompts": [PROMPT_ITEM]}
    assert result["image_assets"]["asset_count"] == 1
    assert result["image_review"]["selected_count"] == 1
    assert isinstance(result["video_prompts"].get("prompts"), list)

    stored_context = runner._session.get_run_context(run_id) or {}
    assert stored_context["character_manifest"] == EXPLICIT_CHARACTER_MANIFEST
    assert stored_context["image_prompts"] == {"prompts": [PROMPT_ITEM]}


def verify_stored_payload_fallback() -> None:
    runner = WorkflowRunner()
    run_id = "run_verify_bug003_stored"
    save_stored_context(runner, run_id)

    result, captured = run_refresh(
        runner,
        run_id,
        storyboard={},
        workflow_input={},
        image_review={},
        character_manifest=None,
        image_prompts=None,
    )

    outputs = captured["outputs"]
    assert outputs["storyboard"]["scenes"] == [SCENE]
    assert outputs["character_manifest"] == STORED_CHARACTER_MANIFEST
    assert outputs["image_prompts"] == STORED_IMAGE_PROMPTS
    assert result["workflow_id"] == "wf_request_bug003"
    assert result["session_id"] == "sess_stored_bug003"


def verify_request_schema_accepts_prompt_shapes() -> None:
    base_payload = {
        "workflow_id": "wf_schema_bug003",
        "run_id": "run_schema_bug003",
        "storyboard": {"scenes": [SCENE]},
        "workflow_input": make_workflow_input(),
        "image_review": make_image_review(),
    }

    list_request = ImageReviewRefreshRequest(
        **base_payload,
        image_prompts=[PROMPT_ITEM],
    )
    assert list_request.image_prompts == [PROMPT_ITEM]

    dict_request = ImageReviewRefreshRequest(
        **base_payload,
        image_prompts={"prompts": [PROMPT_ITEM]},
    )
    assert dict_request.image_prompts == {"prompts": [PROMPT_ITEM]}


def main() -> int:
    verify_request_schema_accepts_prompt_shapes()
    verify_explicit_payload_wins()
    verify_stored_payload_fallback()
    print("[OK] refresh request schema accepts list and dict prompt payloads")
    print("[OK] explicit refresh payload is accepted and normalized")
    print("[OK] stored run context remains the fallback")
    print("PASS: BUG-003 image-review refresh contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
