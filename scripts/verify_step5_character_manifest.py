"""Contract verification for runner refactor Step 5.

Verifies RunnerCharacterManifestSupport in-process so the character
candidate/manifest extraction can be checked without a running API server.

Usage:
    python scripts/verify_step5_character_manifest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import StructuredCharacterInput, WorkflowInput
from app.services.runner import WorkflowRunner


def _assert_structured_manifest(runner: WorkflowRunner) -> None:
    workflow_input = WorkflowInput(
        topic="红色小兔子和蓝色小乌龟合作送信",
        structured_characters_enabled=True,
        characters=[
            StructuredCharacterInput(
                display_name="小兔子",
                species="rabbit",
                role_type="primary",
                visual_traits="red scarf, upright ears",
                forbidden_traits="no turtle shell",
            ),
            StructuredCharacterInput(
                display_name="小乌龟",
                species="turtle",
                role_type="secondary",
                visual_traits="blue shell",
                forbidden_traits="no rabbit ears",
            ),
        ],
    )

    support = runner._character_manifest_support
    candidates = support.build_character_candidates(workflow_input)
    assert candidates == [
        {
            "candidate_id": "candidate_01",
            "display_name": "小兔子",
            "species": "rabbit",
            "role_type": "primary",
            "visual_traits": "red scarf, upright ears",
            "forbidden_traits": "no turtle shell",
            "source": "structured_input",
        },
        {
            "candidate_id": "candidate_02",
            "display_name": "小乌龟",
            "species": "turtle",
            "role_type": "secondary",
            "visual_traits": "blue shell",
            "forbidden_traits": "no rabbit ears",
            "source": "structured_input",
        },
    ]

    manifest = support.build_character_manifest(workflow_input, candidates)
    assert manifest[0]["character_id"] == "char_primary_01"
    assert manifest[0]["signature_traits"] == ["red scarf", "upright ears"]
    assert manifest[0]["forbidden_traits"] == ["no turtle shell"]
    assert manifest[1]["character_id"] == "char_secondary_01"
    assert manifest[1]["signature_traits"] == ["blue shell"]

    enriched = support.enrich_character_manifest_traits_from_topic(
        manifest,
        workflow_input.topic,
    )
    assert "红色" in enriched[0]["signature_traits"]
    assert "red" in enriched[0]["signature_traits"]
    assert "蓝色" in enriched[1]["signature_traits"]
    assert "blue" in enriched[1]["signature_traits"]

    outputs = {
        "character_manifest": {
            "enabled": True,
            "count": len(enriched),
            "characters": enriched,
        }
    }
    assert support.character_manifest_items(outputs) == enriched
    assert support.manifest_character_by_role(outputs, "primary") == enriched[0]
    assert support.manifest_character_by_role(outputs, "secondary") == enriched[1]

    chinese_trait_input = WorkflowInput(
        topic="嘟嘟小车去看海",
        structured_characters_enabled=True,
        characters=[
            StructuredCharacterInput(
                display_name="嘟嘟小车",
                species="小汽车",
                role_type="primary",
                visual_traits="圆圆胖胖的鲜红色车身，黄色圆圆大灯、温柔小笑脸;玩具卡通比例",
                forbidden_traits="不要人物、不要小女孩， 不要绿色车身",
            ),
        ],
    )
    chinese_manifest = support.build_character_manifest(
        chinese_trait_input,
        support.build_character_candidates(chinese_trait_input),
    )
    assert chinese_manifest[0]["signature_traits"] == [
        "圆圆胖胖的鲜红色车身",
        "黄色圆圆大灯",
        "温柔小笑脸",
        "玩具卡通比例",
    ]
    assert chinese_manifest[0]["forbidden_traits"] == [
        "不要人物",
        "不要小女孩",
        "不要绿色车身",
    ]


def _assert_legacy_manifest(runner: WorkflowRunner) -> None:
    workflow_input = WorkflowInput(
        topic="小狐狸帮小猫找风筝",
        main_character_display="小狐狸",
        main_character_species="fox",
        main_character_visual_traits="orange tail, green vest",
        secondary_character_display="小猫",
        secondary_character_species="cat",
        secondary_character_visual_traits="white paws",
    )

    support = runner._character_manifest_support
    candidates = support.build_character_candidates(workflow_input)
    assert [item["source"] for item in candidates] == [
        "legacy_main_character",
        "legacy_secondary_character",
    ]
    assert candidates[0]["candidate_id"] == "candidate_01"
    assert candidates[1]["candidate_id"] == "candidate_02"

    manifest = support.build_character_manifest(workflow_input, candidates)
    assert manifest[0]["display_name"] == "小狐狸"
    assert manifest[0]["species"] == "fox"
    assert manifest[1]["display_name"] == "小猫"
    assert manifest[1]["role_type"] == "secondary"


def _assert_visual_profile_merge(runner: WorkflowRunner) -> None:
    support = runner._character_manifest_support
    character_manifest = {
        "enabled": True,
        "count": 2,
        "characters": [
            {
                "character_id": "char_primary_01",
                "display_name": "小兔子",
                "species": "rabbit",
                "role_type": "primary",
                "signature_traits": ["red scarf"],
                "forbidden_traits": ["no shell"],
            },
            {
                "character_id": "char_secondary_01",
                "display_name": "小乌龟",
                "species": "turtle",
                "role_type": "secondary",
                "signature_traits": [],
                "forbidden_traits": [],
            },
        ],
    }
    profiles = {
        "profiles": [
            {
                "character_id": "char_primary_01",
                "display_name": "小兔子",
                "species": "rabbit",
                "must_keep": ["red scarf", "upright ears"],
                "must_avoid": "no shell，no wings",
                "visual_identity": "stable rabbit design",
                "profile_source": "test",
                "llm_profile_ready": True,
            }
        ]
    }

    enriched = support.apply_visual_profiles_to_character_manifest(
        character_manifest,
        profiles,
    )
    primary = enriched["characters"][0]
    secondary = enriched["characters"][1]

    assert primary["signature_traits"] == ["red scarf", "upright ears"]
    assert primary["forbidden_traits"] == ["no shell", "no wings"]
    assert primary["visual_identity"] == "stable rabbit design"
    assert primary["profile_source"] == "test"
    assert primary["llm_profile_ready"] is True
    assert secondary == character_manifest["characters"][1]


def main() -> int:
    runner = WorkflowRunner()
    _assert_structured_manifest(runner)
    print("[OK] structured character manifest")
    _assert_legacy_manifest(runner)
    print("[OK] legacy character manifest")
    _assert_visual_profile_merge(runner)
    print("[OK] visual profile manifest merge")
    print("PASS: Step 5 character manifest support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
