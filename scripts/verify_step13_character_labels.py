"""Contract verification for runner refactor Step 13.

Verifies RunnerCharacterLabelsSupport keeps topic cleanup, character display
fallbacks, secondary-character detection, and consistency anchors stable while
WorkflowRunner delegates through thin wrappers.

Usage:
    python scripts/verify_step13_character_labels.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import StepContext, WorkflowRunner


def make_ctx(**overrides: object) -> StepContext:
    data = {
        "topic": "写一个关于小兔子过河的故事",
        "duration_sec": 60,
    }
    data.update(overrides)
    return StepContext(
        workflow_id="verify_step13",
        session_id=None,
        run_id="run_verify_step13",
        input=WorkflowInput(**data),
    )


def main() -> int:
    runner = WorkflowRunner()
    support = runner._character_labels

    assert runner._clean_story_topic("  写一个关于小兔子过河的故事。 ") == "小兔子过河的故事"
    assert runner._clean_story_topic("写一个关于小兔子过河的故事") == "小兔子过河"
    assert support.clean_story_topic("关于小汽车冒险短片") == "小汽车冒险"

    topic_ctx = make_ctx()
    assert runner._topic_primary_character_display_label(topic_ctx) == "小兔子"
    assert (
        runner._topic_primary_character_display_label(topic_ctx)
        == support.topic_primary_character_display_label(topic_ctx)
    )

    manifest_outputs = {
        "character_manifest": {
            "characters": [
                {
                    "display_name": "小白兔",
                    "species": "rabbit",
                    "role_type": "primary",
                    "visual_traits": "white fur, long ears, red scarf",
                    "forbidden_traits": "turtle shell, cat ears",
                },
                {
                    "display_name": "小乌龟",
                    "species": "turtle",
                    "role_type": "secondary",
                },
            ]
        }
    }
    assert runner._main_character_display_label(topic_ctx, manifest_outputs) == "小白兔"
    assert (
        runner._main_character_display_label(topic_ctx, manifest_outputs)
        == support.main_character_display_label(topic_ctx, manifest_outputs)
    )
    assert (
        runner._secondary_character_display_label(topic_ctx, manifest_outputs)
        == "小乌龟"
    )
    assert runner._has_secondary_character(topic_ctx, manifest_outputs) is True

    explicit_ctx = make_ctx(
        main_character="small rabbit",
        main_character_display="小小兔",
        secondary_character="small turtle",
        secondary_character_display="慢慢龟",
    )
    assert runner._main_character_display_label(explicit_ctx) == "小小兔"
    assert runner._secondary_character_display_label(explicit_ctx) == "慢慢龟"
    assert runner._main_character_label(explicit_ctx) == "small rabbit"
    assert runner._main_character_subject(explicit_ctx) == "small rabbit"

    generic_ctx = make_ctx(topic="讲一个关于小蝌蚪找妈妈的故事")
    constraints = runner._visual_subject_constraints("小蝌蚪")
    assert constraints == support.visual_subject_constraints("小蝌蚪")
    assert "tadpole" in constraints
    assert "no adult frog body" in constraints

    anchor_ctx = make_ctx(character_consistency_anchor="exact anchor")
    assert runner._character_consistency_anchor(anchor_ctx) == "exact anchor"

    manifest_anchor = runner._character_consistency_anchor(
        topic_ctx,
        manifest_outputs,
    )
    assert manifest_anchor == support.character_consistency_anchor(
        topic_ctx,
        manifest_outputs,
    )
    assert "小白兔 (rabbit)" in manifest_anchor
    assert "white fur, long ears, red scarf" in manifest_anchor
    assert "avoid: turtle shell, cat ears" in manifest_anchor
    assert "same character across all scenes" in manifest_anchor

    explicit_anchor = runner._character_consistency_anchor(explicit_ctx)
    assert "main subject: small rabbit" in explicit_anchor
    assert "same main subject across all scenes" in explicit_anchor

    derived_anchor = runner._character_consistency_anchor(generic_ctx)
    assert "main subject: 小蝌蚪" in derived_anchor
    assert "no frog legs" in derived_anchor

    fallback_ctx = make_ctx(topic="   ", character_style="fantasy")
    fallback_anchor = runner._character_consistency_anchor(fallback_ctx)
    assert fallback_anchor.startswith("main subject: 奇幻角色")
    assert runner._main_character_display_label(fallback_ctx) == "奇幻角色"

    print("verify_step13_character_labels: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
