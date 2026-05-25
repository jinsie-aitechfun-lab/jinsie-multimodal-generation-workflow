"""Contract verification for runner refactor Step 6.

Verifies RunnerSceneCharactersSupport in-process so scene-level character
binding, prompt blocks, and metadata character id extraction stay stable.

Usage:
    python scripts/verify_step6_scene_characters.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.runner import WorkflowRunner


OUTPUTS = {
    "character_manifest": {
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
}

SCENE = {
    "scene_id": "scene_01",
    "scene_title": "一起过河",
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
}


def main() -> int:
    runner = WorkflowRunner()
    support = runner._scene_characters

    bindings = support.scene_character_bindings(OUTPUTS)
    assert bindings == SCENE["characters"], bindings

    primary = support.manifest_character_by_id(OUTPUTS, "char_primary_01")
    assert primary and primary["display_name"] == "小兔子"
    assert support.manifest_character_by_id(OUTPUTS, "") is None

    enriched = support.enriched_scene_characters_from_manifest(OUTPUTS, SCENE)
    assert len(enriched) == 2
    assert enriched[0]["visual_identity"] == "stable rabbit design"
    assert enriched[1]["signature_traits"] == ["round green shell", "short legs"]

    required_block = support.scene_character_required_presence_block(OUTPUTS, SCENE)
    assert "required scene characters: 小兔子 and 小乌龟" in required_block
    assert "not a solo portrait" in required_block
    assert "include all of 小兔子 and 小乌龟 together" in required_block
    assert "小兔子 may lead the action" in required_block
    assert "小乌龟 must be clearly visible near 小兔子" in required_block

    prompt_block = support.scene_character_prompt_block(OUTPUTS, SCENE)
    assert "scene cast lock" in prompt_block
    assert "name: 小兔子" in prompt_block
    assert "must keep: long upright ears, red scarf" in prompt_block
    assert "must avoid: no rabbit ears" in prompt_block
    assert "cross-character must avoid" in prompt_block
    assert "no turtle shell" in prompt_block
    assert "no long upright rabbit ears" in prompt_block

    negative_block = support.scene_character_negative_block(OUTPUTS, SCENE)
    assert negative_block.startswith("subject negative constraints: ")
    assert "no turtle shell" in negative_block
    assert "小兔子: no turtle shell" in negative_block
    assert "小乌龟: no rabbit ears" in negative_block
    assert "missing required scene character" in negative_block
    assert negative_block.count("no turtle shell") == 2

    character_ids = support.character_ids_from_bindings(
        SCENE["characters"]
        + [{"character_id": "char_primary_01"}, {"character_id": ""}, "bad-item"]
    )
    assert character_ids == ["char_primary_01", "char_secondary_01"], character_ids
    character_names = support.character_names_from_bindings(
        SCENE["characters"]
        + [{"display_name": "小兔子"}, {"species": "bad"}, "bad-item"]
    )
    assert character_names == ["小兔子", "小乌龟", "bad"], character_names

    print("[OK] scene character bindings")
    print("[OK] scene character prompt contracts")
    print("[OK] scene character id metadata")
    print("PASS: Step 6 scene character support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
