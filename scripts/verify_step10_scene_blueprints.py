"""Contract verification for runner refactor Step 10.

Verifies RunnerSceneBlueprintsSupport keeps scene blueprint templates and
expansion behavior stable while WorkflowRunner delegates through thin wrappers.

Usage:
    python scripts/verify_step10_scene_blueprints.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import WorkflowRunner


def build_ctx(runner: WorkflowRunner, *, secondary: bool):
    workflow_input = WorkflowInput(
        topic="小兔子和小乌龟一起过河" if secondary else "小兔子过河",
        duration_sec=120,
        audio_enabled=False,
    )
    outputs = {
        "character_manifest": {
            "enabled": True,
            "count": 2 if secondary else 1,
            "characters": [
                {
                    "character_id": "char_primary_01",
                    "display_name": "小兔子",
                    "species": "小兔子",
                    "role_type": "primary",
                },
            ]
            + (
                [
                    {
                        "character_id": "char_secondary_01",
                        "display_name": "小乌龟",
                        "species": "小乌龟",
                        "role_type": "secondary",
                    }
                ]
                if secondary
                else []
            ),
        }
    }
    ctx = runner._build_step_context(
        workflow_id="verify-step10",
        session_id="verify-session",
        run_id="run_verify_step10",
        workflow_input=workflow_input,
    )
    return ctx, outputs


def main() -> int:
    runner = WorkflowRunner()
    support = runner._scene_blueprints_support

    expanded = runner._expand_scene_blueprints(
        [
            {
                "scene_title": "A",
                "visual_description": "A desc",
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "B",
                "visual_description": "B desc",
                "shot_type": "medium",
                "transition": "cut",
            },
        ],
        5,
    )
    assert expanded == support.expand_scene_blueprints(expanded[:2], 5)
    assert [item["scene_title"] for item in expanded] == [
        "A",
        "B",
        "A · 延展 2",
        "B · 延展 2",
        "A · 延展 3",
    ]
    assert runner._expand_scene_blueprints([], 3) == []
    assert runner._expand_scene_blueprints(expanded, 0) == []

    ctx_single, outputs_single = build_ctx(runner, secondary=False)
    single = runner._scene_blueprints(ctx_single, 6, outputs_single)
    assert single == support.scene_blueprints(ctx_single, 6, outputs_single)
    assert len(single) == 6
    assert single[0]["scene_title"] == "故事开场"
    assert "主角小兔子第一次出场" in single[0]["visual_description"]
    assert "小乌龟" not in single[0]["visual_description"]
    assert single[1]["transition"] == "cut"

    ctx_multi, outputs_multi = build_ctx(runner, secondary=True)
    multi = runner._scene_blueprints(ctx_multi, 7, outputs_multi)
    assert multi == support.scene_blueprints(ctx_multi, 7, outputs_multi)
    assert len(multi) == 7
    assert "主角小兔子和朋友小乌龟第一次一起出场" in multi[0][
        "visual_description"
    ]
    assert multi[6]["scene_title"] == "故事开场 · 延展 2"
    assert multi[6]["shot_type"] == "wide"
    assert multi[6]["transition"] == "fade"

    print("[OK] scene blueprint expansion contract")
    print("[OK] single-character blueprint contract")
    print("[OK] multi-character blueprint contract")
    print("[OK] runner scene blueprint proxy contract")
    print("PASS: Step 10 scene blueprint support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
