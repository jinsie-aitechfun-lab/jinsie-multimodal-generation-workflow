from __future__ import annotations

from app.services.runner import WorkflowRunner
from app.services.runner_image_prompts_support import (
    ensure_character_identity_lock,
)
from app.services.topic_character_infer import infer_primary_character_manifest


def _red_panda_character() -> dict:
    return {
        "character_id": "char_primary_01",
        "display_name": "小熊猫",
        "species": "小熊猫",
        "role_type": "primary",
        "visual_identity": (
            "A small red panda with rust-red fur, dark legs, a white facial mask, "
            "rounded ears, and a long ringed tail."
        ),
        "signature_traits": [
            "rust-red fur",
            "white facial mask",
            "long ringed tail",
        ],
    }


def test_red_panda_is_not_inferred_as_cat() -> None:
    assert infer_primary_character_manifest("小熊猫的森林冒险") is None
    assert infer_primary_character_manifest("一只小熊猫帮助朋友") is None

    cat = infer_primary_character_manifest("小猫的故事")
    assert cat is not None
    assert cat["species"] == "cat"


def test_manifest_fallback_preserves_full_subject_identity() -> None:
    runner = WorkflowRunner()
    manifest = runner._character_manifest_support.ensure_fallback_character_identities(
        [
            {
                "character_id": "char_primary_01",
                "display_name": "小熊猫",
                "species": "小熊猫",
                "role_type": "primary",
                "signature_traits": [],
                "forbidden_traits": [],
            }
        ]
    )

    character = manifest[0]
    assert "小熊猫" in character["visual_identity"]
    assert "indivisible" in " ".join(character["signature_traits"])
    assert "小猫" not in character["visual_identity"]


def test_single_character_pronoun_prompt_keeps_identity() -> None:
    prompt = ensure_character_identity_lock(
        "它抱着果子继续向森林深处走去。",
        [_red_panda_character()],
    )

    assert prompt.startswith("provider character identity lock:")
    assert "小熊猫 is exactly 小熊猫" in prompt
    assert "rust-red fur" in prompt
    assert "long ringed tail" in prompt
    assert "pronoun" in prompt
    assert prompt.endswith("它抱着果子继续向森林深处走去。")


def test_generic_nickname_prompt_keeps_identity_without_duplicate_lock() -> None:
    prompt = ensure_character_identity_lock(
        "小家伙抬头看向星空。",
        [_red_panda_character()],
    )
    repeated = ensure_character_identity_lock(prompt, [_red_panda_character()])

    assert "小熊猫 is exactly 小熊猫" in prompt
    assert repeated == prompt
    assert repeated.count("provider character identity lock:") == 1


def test_multi_character_prompt_keeps_every_identity() -> None:
    companion = {
        "character_id": "char_secondary_01",
        "display_name": "月月",
        "species": "萤火虫",
        "role_type": "secondary",
        "visual_identity": "A tiny golden firefly with two translucent wings.",
        "signature_traits": ["golden glow", "two translucent wings"],
    }

    prompt = ensure_character_identity_lock(
        "它们一起穿过夜色。",
        [_red_panda_character(), companion],
    )

    assert "小熊猫 is exactly 小熊猫" in prompt
    assert "月月 is exactly 萤火虫" in prompt
    assert prompt.count("provider character identity lock:") == 1
