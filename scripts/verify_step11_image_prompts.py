"""Contract verification for runner refactor Step 11.

Verifies RunnerImagePromptsSupport keeps scene-level and shot-level image
prompt assembly stable while WorkflowRunner delegates through a thin wrapper.

Usage:
    python scripts/verify_step11_image_prompts.py
"""

from __future__ import annotations

import copy
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
            "species": "rabbit",
            "role_type": "primary",
            "signature_traits": ["long upright ears", "red scarf"],
            "forbidden_traits": ["no turtle shell"],
            "visual_identity": "stable rabbit design",
        },
        {
            "character_id": "char_secondary_01",
            "display_name": "小乌龟",
            "species": "turtle",
            "role_type": "secondary",
            "signature_traits": ["round green shell", "short legs"],
            "forbidden_traits": ["no rabbit ears"],
            "visual_identity": "stable turtle design",
        },
    ],
}

SCENES = [
    {
        "scene_id": "scene_01",
        "scene_title": "一起过河",
        "visual_description": "小兔子和小乌龟站在河边，一起观察水流。",
        "narration": "小兔子和小乌龟来到河边。",
        "duration_sec": 10,
        "shot_type": "wide",
        "transition": "fade",
        "characters": [
            {
                "character_id": "char_primary_01",
                "display_name": "小兔子",
                "species": "rabbit",
                "role_type": "primary",
            },
            {
                "character_id": "char_secondary_01",
                "display_name": "小乌龟",
                "species": "turtle",
                "role_type": "secondary",
            },
        ],
    },
    {
        "scene_id": "scene_02",
        "scene_title": "搭起小桥",
        "visual_description": "两个朋友把树枝和荷叶放在一起，慢慢搭成小桥。",
        "narration": "它们一起想办法搭桥。",
        "duration_sec": 10,
        "shot_type": "medium",
        "transition": "cut",
        "characters": [
            {
                "character_id": "char_primary_01",
                "display_name": "小兔子",
                "species": "rabbit",
                "role_type": "primary",
            },
            {
                "character_id": "char_secondary_01",
                "display_name": "小乌龟",
                "species": "turtle",
                "role_type": "secondary",
            },
        ],
    },
]


def build_ctx(runner: WorkflowRunner):
    workflow_input = WorkflowInput(
        topic="小兔子和小乌龟一起过河",
        duration_sec=60,
        audience="children",
        tone="warm",
        visual_style="storybook",
        character_style="animal",
        audio_enabled=False,
        structured_characters_enabled=True,
        characters=[
            {
                "display_name": "小兔子",
                "species": "rabbit",
                "role_type": "primary",
                "visual_traits": "long upright ears, red scarf",
                "forbidden_traits": "no turtle shell",
            },
            {
                "display_name": "小乌龟",
                "species": "turtle",
                "role_type": "secondary",
                "visual_traits": "round green shell, short legs",
                "forbidden_traits": "no rabbit ears",
            },
        ],
    )
    return runner._build_step_context(
        workflow_id="verify-step11",
        session_id="verify-session",
        run_id="run_verify_step11",
        workflow_input=workflow_input,
    )


def build_scene_outputs() -> dict:
    return {
        "character_manifest": copy.deepcopy(CHARACTER_MANIFEST),
        "storyboard": {
            "scene_count": len(SCENES),
            "total_duration_sec": 20,
            "scenes": copy.deepcopy(SCENES),
        },
    }


def build_shot_outputs() -> dict:
    outputs = build_scene_outputs()
    outputs["sentence_shots"] = {
        "enabled": True,
        "shot_count": 2,
        "items": [
            {
                "shot_id": "shot_01",
                "scene_id": "scene_01",
                "scene_title": "一起过河",
                "visual_description": "小兔子和小乌龟站在河边，一起观察水流。",
                "shot_type": "wide",
                "transition": "fade",
                "text": "小兔子和小乌龟来到河边。",
            },
            {
                "shot_id": "shot_02",
                "scene_id": "scene_02",
                "scene_title": "搭起小桥",
                "visual_description": "两个朋友把树枝和荷叶放在一起。",
                "shot_type": "medium",
                "transition": "cut",
                "text": "它们一起想办法搭桥。",
            },
        ],
    }
    return outputs


def main() -> int:
    os.environ["CHARACTER_PROFILE_PROVIDER"] = "template"

    runner = WorkflowRunner()
    support = runner._image_prompts
    ctx = build_ctx(runner)

    scene_outputs = build_scene_outputs()
    direct_scene_outputs = copy.deepcopy(scene_outputs)
    scene_result = runner._run_image_prompts(ctx, scene_outputs)
    direct_scene_result = support.run_image_prompts(ctx, direct_scene_outputs)
    assert scene_result == direct_scene_result
    assert scene_result["provider"] == "image_prompt_builder"
    assert len(scene_result["prompts"]) == 2
    assert scene_result["character_visual_profiles"]["count"] == 2
    assert scene_result["character_anchor"]["provider_reference_support"][
        "mode"
    ] == "metadata_only"

    first_scene_prompt = scene_result["prompts"][0]["prompt"]
    assert "storybook illustration" in first_scene_prompt
    assert "scene cast lock" in first_scene_prompt
    assert "required scene characters" in first_scene_prompt
    assert "character separation" in first_scene_prompt
    assert "scene action binding" in first_scene_prompt
    assert "subject negative constraints" in first_scene_prompt
    assert "no turtle shell" in first_scene_prompt
    assert "cross-character must avoid" in first_scene_prompt
    assert scene_result["prompts"][0]["required_character_ids"] == [
        "char_primary_01",
        "char_secondary_01",
    ]
    assert scene_result["prompts"][0]["required_character_names"] == [
        "小兔子",
        "小乌龟",
    ]
    first_character = scene_result["prompts"][0]["characters"][0]
    assert first_character["character_id"] == "char_primary_01"
    assert first_character["display_name"] == "小兔子"
    assert "long upright ears" in first_character["signature_traits"]
    assert "same character identity: 小兔子" in first_character["signature_traits"]
    assert "no turtle shell" in first_character["forbidden_traits"]
    assert first_character["visual_identity"]

    shot_outputs = build_shot_outputs()
    direct_shot_outputs = copy.deepcopy(shot_outputs)
    shot_result = runner._run_image_prompts(ctx, shot_outputs)
    direct_shot_result = support.run_image_prompts(ctx, direct_shot_outputs)
    assert shot_result == direct_shot_result
    assert len(shot_result["prompts"]) == 2
    assert shot_result["prompts"][0]["shot_id"] == "shot_01"
    assert shot_result["prompts"][0]["characters"] == SCENES[0]["characters"]
    assert shot_result["prompts"][0]["required_character_ids"] == [
        "char_primary_01",
        "char_secondary_01",
    ]
    assert shot_result["prompts"][0]["required_character_names"] == [
        "小兔子",
        "小乌龟",
    ]
    assert "story context: 小兔子和小乌龟来到河边。" in shot_result["prompts"][0][
        "prompt"
    ]

    print("[OK] scene-level image prompt contract")
    print("[OK] shot-level image prompt contract")
    print("[OK] character anchor metadata contract")
    print("[OK] runner image prompt proxy contract")
    print("PASS: Step 11 image prompt support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
