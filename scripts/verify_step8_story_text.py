"""Contract verification for runner refactor Step 8.

Verifies RunnerStoryTextSupport keeps story plans, labels, sanitization, and
template paragraph contracts stable while WorkflowRunner delegates through
thin compatibility wrappers.

Usage:
    python scripts/verify_step8_story_text.py
"""

from __future__ import annotations

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
        },
        {
            "character_id": "char_secondary_01",
            "display_name": "小乌龟",
            "species": "小乌龟",
            "role_type": "secondary",
        },
    ],
}


def main() -> int:
    runner = WorkflowRunner()
    support = runner._story_text

    assert runner._scene_count(60) == support.scene_count(60) == 6
    assert runner._scene_count(120) == support.scene_count(120) == 12
    assert runner._scene_count(180) == support.scene_count(180) == 18
    assert runner._duration_story_plan(60) == {
        "duration_sec": 60,
        "scene_count": 6,
        "target_min_chars": 420,
        "target_max_chars": 520,
        "target_chars": 470,
    }
    assert runner._duration_story_plan(90)["scene_count"] == 12

    noisy_text = """
    user
    小兔子过河
    123
    assistant: draft
    标题 1
    在一个阳光明亮的早晨，小兔子和小乌龟准备一起过河。
    """
    cleaned = runner._sanitize_llm_story_text(noisy_text, "小兔子过河")
    assert cleaned == "在一个阳光明亮的早晨，小兔子和小乌龟准备一起过河。"
    assert cleaned == support.sanitize_llm_story_text(noisy_text, "小兔子过河")

    assert runner._story_text_has_blocked_tokens("hero species=rabbit") is True
    assert runner._story_text_has_blocked_tokens("温暖的小故事") is False
    assert runner._story_text_char_count(" 小 兔 子 \n 过 河 ") == 5
    assert runner._audience_label("children") == "小朋友"
    assert runner._tone_label("warm") == "温暖"
    assert runner._visual_style_label("storybook") == "绘本"
    assert runner._character_style_label("animal") == "小动物"

    workflow_input = WorkflowInput(
        topic="小兔子和小乌龟一起过河",
        duration_sec=120,
        audio_enabled=False,
    )
    ctx = runner._build_step_context(
        workflow_id="verify-step8",
        session_id="verify-session",
        run_id="run_verify_step8",
        workflow_input=workflow_input,
    )
    outputs = {"character_manifest": CHARACTER_MANIFEST}
    paragraphs = runner._build_story_paragraphs(ctx, outputs)
    direct_paragraphs = support.build_story_paragraphs(ctx, outputs)

    assert paragraphs == direct_paragraphs
    assert len(paragraphs) == 7
    assert "小兔子" in paragraphs[0]
    assert "小乌龟" in paragraphs[0]

    workflow_input_60 = WorkflowInput(
        topic="小兔子和小乌龟一起过河",
        duration_sec=60,
        audio_enabled=True,
        voiceover_enabled=True,
    )
    ctx_60 = runner._build_step_context(
        workflow_id="verify-step8-60",
        session_id="verify-session",
        run_id="run_verify_step8_60",
        workflow_input=workflow_input_60,
    )
    story_60 = runner._run_story(ctx_60, outputs)
    story_plan_60 = runner._duration_story_plan(60)
    assert (
        runner._story_text_char_count(story_60["text"])
        >= story_plan_60["target_min_chars"] - 10
    )

    print("[OK] story duration plan helpers")
    print("[OK] story sanitization helpers")
    print("[OK] story label helpers")
    print("[OK] story paragraph template contracts")
    print("PASS: Step 8 story text support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
