"""Contract verification for runner refactor Step 4 (RunnerVideoPromptsSupport).

This is intentionally in-process instead of HTTP-based: video prompt building is
pure data assembly, so the script can verify the extracted support module
without requiring a running FastAPI server.

Usage:
    python scripts/verify_step4_video_prompts.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import WorkflowRunner


SCENES: List[Dict[str, Any]] = [
    {
        "scene_id": "scene_01",
        "scene_title": "初遇",
        "visual_description": "小兔子在清晨的菜园里发现一封信。",
        "narration": "小兔子收到了一项温柔的任务。",
        "duration_sec": 6,
        "shot_type": "wide",
        "transition": "fade",
        "characters": [
            {"character_id": "char_primary_01", "display_name": "小兔子"},
            {"character_id": "char_primary_01", "display_name": "小兔子"},
            {"character_id": "char_secondary_01", "display_name": "小乌龟"},
        ],
    },
    {
        "scene_id": "scene_02",
        "scene_title": "",
        "visual_description": "",
        "narration": "",
        "duration_sec": 5,
        "characters": "invalid-shape",
    },
]

OUTPUTS: Dict[str, Any] = {
    "image_review": {
        "selected_assets": [
            {
                "scene_id": "scene_01",
                "selected_asset_ref": {
                    "asset_id": "img_scene_01_a",
                    "uri": "assets/mock/image/scene_01.png",
                },
                "selection_source": "auto",
                "selection_mode": "best_candidate",
                "review_status": "selected",
            }
        ]
    }
}


def _ctx(runner: WorkflowRunner, provider: str):
    workflow_input = WorkflowInput(
        topic="小兔子送信",
        visual_style="watercolor storybook",
        tone="warm",
        character_style="animal",
        main_character="小兔子",
        main_character_display="小兔子",
        video_provider=provider,
    )
    return runner._build_step_context(
        workflow_id=f"wf-step4-{provider}",
        session_id="sess-step4",
        run_id="run_step4",
        workflow_input=workflow_input,
    )


def _assert_prompt_contract(payload: Dict[str, Any], provider: str) -> None:
    assert payload.get("provider") == provider, payload
    prompts = payload.get("prompts")
    assert isinstance(prompts, list) and len(prompts) == len(SCENES), payload

    first = prompts[0]
    assert first.get("scene_id") == "scene_01"
    assert first.get("provider") == provider
    assert first.get("duration_sec") == 6
    assert first.get("shot_type") == "wide"
    assert first.get("transition") == "fade"
    assert first.get("character_ids") == [
        "char_primary_01",
        "char_secondary_01",
    ], first
    assert first.get("selected_asset_ref") == {
        "asset_id": "img_scene_01_a",
        "uri": "assets/mock/image/scene_01.png",
    }
    assert first.get("image_asset_ref") == first.get("selected_asset_ref")
    assert first.get("selection_source") == "auto"
    assert first.get("selection_mode") == "best_candidate"
    assert first.get("review_status") == "selected"

    second = prompts[1]
    assert second.get("scene_title") == "scene_02"
    assert second.get("shot_type") == "medium"
    assert second.get("transition") == "fade"
    assert second.get("characters") == []
    assert second.get("character_ids") == []
    assert second.get("selected_asset_ref") == {}
    assert second.get("selection_source") == "unknown"
    assert second.get("selection_mode") == "unknown"
    assert second.get("review_status") == "unreviewed"

    prompt_text = str(first.get("prompt") or "")
    assert "小兔子" in prompt_text
    assert SCENES[0]["visual_description"] in prompt_text


def main() -> int:
    runner = WorkflowRunner()

    for provider in ("mock", "kling", "jimeng"):
        ctx = _ctx(runner, provider)
        payload = runner._video_prompts.build_video_provider_prompts(
            ctx=ctx,
            scenes=SCENES,
            outputs=OUTPUTS,
        )
        _assert_prompt_contract(payload, provider)
        print(f"[OK] {provider} video prompt contract")

    print("PASS: Step 4 video prompt support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
