"""Contract verification for runner refactor Step 7.

Verifies RunnerStorySupport keeps the story step output contract stable while
WorkflowRunner delegates the story step through the extracted support class.

Usage:
    python scripts/verify_step7_story_support.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import WorkflowRunner


CHARACTER_MANIFEST = {
    "enabled": True,
    "count": 2,
    "characters": [
        {
            "character_id": "char_primary_01",
            "display_name": "小兔子",
            "species": "小兔子",
            "role_type": "primary",
            "signature_traits": ["white fur", "red scarf"],
            "forbidden_traits": [],
        },
        {
            "character_id": "char_secondary_01",
            "display_name": "小乌龟",
            "species": "小乌龟",
            "role_type": "secondary",
            "signature_traits": ["green shell"],
            "forbidden_traits": [],
        },
    ],
}


def main() -> int:
    os.environ["STORY_PROVIDER"] = "template"

    runner = WorkflowRunner()
    workflow_input = WorkflowInput(
        topic="小兔子和小乌龟一起过河",
        audience="children",
        tone="warm",
        visual_style="storybook",
        character_style="animal",
        duration_sec=60,
        audio_enabled=False,
    )
    ctx = runner._build_step_context(
        workflow_id="verify-step7",
        session_id="verify-session",
        run_id="run_verify_step7",
        workflow_input=workflow_input,
    )
    outputs = {"character_manifest": CHARACTER_MANIFEST}

    story = runner._run_story(ctx, outputs)

    assert story["title"] == "小兔子和小乌龟一起过河的故事"
    assert story["generation_source"] == "template_fallback"
    assert story["fallback_reason"] == "story_provider_template"
    assert "小兔子和小乌龟一起过河" in story["summary"]
    assert "小兔子" in story["summary"]
    assert "小乌龟" in story["summary"]
    assert "小兔子" in story["text"]
    assert story["style_profile"]["audience"] == "children"
    assert story["style_profile"]["tone"] == "warm"
    assert story["style_profile"]["visual_style"] == "storybook"
    assert story["style_profile"]["character_style"] == "animal"
    assert story["style_profile"]["character_ids"] == [
        "char_primary_01",
        "char_secondary_01",
    ]

    direct_story = runner._story_support.run_story(ctx, outputs)
    assert story == direct_story

    print("[OK] story support template output contract")
    print("[OK] story style profile contract")
    print("[OK] runner story proxy contract")
    print("PASS: Step 7 story support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
