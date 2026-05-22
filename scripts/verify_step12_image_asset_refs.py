"""Contract verification for runner refactor Step 12.

Verifies RunnerImageAssetRefsSupport keeps image asset refs, prompt maps,
metadata, mock candidate refs, and scene candidate variants stable while
WorkflowRunner delegates through thin wrappers.

Usage:
    python scripts/verify_step12_image_asset_refs.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.runner import WorkflowRunner


SCENE = {
    "scene_id": "scene_01",
    "scene_title": "一起过河",
    "visual_description": "小兔子和小乌龟站在河边。",
    "narration": "两个朋友来到河边。",
    "shot_type": "wide",
    "characters": [
        {
            "character_id": "char_primary_01",
            "display_name": "小兔子",
            "role_type": "primary",
        },
        {
            "character_id": "char_secondary_01",
            "display_name": "小乌龟",
            "role_type": "secondary",
        },
    ],
}


def main() -> int:
    runner = WorkflowRunner()
    support = runner._image_asset_refs

    outputs = {
        "image_assets": {
            "assets": [
                {
                    "scene_id": "scene_01",
                    "file_name": "scene_01.png",
                    "relative_path": "assets/mock/verify_step12/scene_01.png",
                    "public_url": "/assets/mock/verify_step12/scene_01.png",
                    "mime_type": "image/png",
                },
                "bad-item",
                {"scene_id": ""},
            ]
        },
        "image_prompts": {
            "prompts": [
                {
                    "scene_id": "scene_01",
                    "shot_id": "shot_01",
                    "scene_title": "一起过河 prompt",
                    "characters": SCENE["characters"],
                    "prompt": "storybook prompt",
                },
                {
                    "scene_id": "scene_02",
                    "prompt": "second prompt",
                },
                "bad-item",
            ]
        },
    }

    by_scene = runner._image_asset_by_scene_id(outputs)
    assert by_scene == support.image_asset_by_scene_id(outputs)
    assert set(by_scene.keys()) == {"scene_01"}

    item = by_scene["scene_01"]
    asset_ref = runner._image_asset_ref_from_item(item, "api_image_generator")
    assert asset_ref == support.image_asset_ref_from_item(item, "api_image_generator")
    assert asset_ref == {
        "scene_id": "scene_01",
        "file_name": "scene_01.png",
        "relative_path": "assets/mock/verify_step12/scene_01.png",
        "public_url": "/assets/mock/verify_step12/scene_01.png",
        "mime_type": "image/png",
        "provider": "api_image_generator",
    }

    prompt_by_scene, prompt_by_shot = runner._image_prompt_item_maps(outputs)
    direct_prompt_by_scene, direct_prompt_by_shot = support.image_prompt_item_maps(
        outputs
    )
    assert prompt_by_scene == direct_prompt_by_scene
    assert prompt_by_shot == direct_prompt_by_shot
    assert set(prompt_by_scene.keys()) == {"scene_01", "scene_02"}
    assert set(prompt_by_shot.keys()) == {"shot_01"}

    metadata = runner._image_asset_metadata(
        scene=SCENE,
        prompt_item=prompt_by_scene["scene_01"],
        fallback_scene_title="fallback title",
    )
    assert metadata == support.image_asset_metadata(
        scene=SCENE,
        prompt_item=prompt_by_scene["scene_01"],
        fallback_scene_title="fallback title",
    )
    assert metadata["scene_title"] == "一起过河 prompt"
    assert metadata["character_ids"] == ["char_primary_01", "char_secondary_01"]
    assert metadata["prompt"] == "storybook prompt"

    variant_a = runner._scene_candidate_variant(scene=SCENE, candidate_index=0)
    variant_b = runner._scene_candidate_variant(scene=SCENE, candidate_index=1)
    assert variant_a == support.scene_candidate_variant(scene=SCENE, candidate_index=0)
    assert variant_b == support.scene_candidate_variant(scene=SCENE, candidate_index=1)
    assert variant_a["candidate_key"] == "candidate_a"
    assert variant_a["candidate_label"] == "Primary Composition"
    assert variant_b["candidate_key"] == "candidate_b"
    assert variant_b["candidate_label"] == "Alternate Composition"
    assert variant_b["shot_type"] == "medium"
    assert variant_b["scene_title"] == "一起过河 Alt"
    assert "alternate composition" in variant_b["visual_description"]

    assets_root = PROJECT_ROOT / "assets" / "mock"
    assets_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="verify_step12_", dir=assets_root) as tmp:
        tmp_path = Path(tmp)
        relative_dir = tmp_path.relative_to(PROJECT_ROOT)
        source = tmp_path / "scene_01.png"
        source.write_bytes(b"fake-png-bytes")

        copy_item = {
            "scene_id": "scene_01",
            "file_name": "scene_01.png",
            "relative_path": str(relative_dir / "scene_01.png"),
            "public_url": f"/{relative_dir}/scene_01.png",
            "mime_type": "image/png",
        }
        candidate_refs = runner._build_mock_candidate_asset_refs(
            copy_item,
            "pillow_storybook_renderer",
        )
        assert candidate_refs == support.build_mock_candidate_asset_refs(
            copy_item,
            "pillow_storybook_renderer",
        )
        assert len(candidate_refs) == 2
        assert candidate_refs[1]["file_name"] == "scene_01__candidate_b.png"
        target = PROJECT_ROOT / str(candidate_refs[1]["relative_path"])
        assert target.exists()
        assert target.read_bytes() == b"fake-png-bytes"

    assert runner._scene_index_by_id([SCENE, {"scene_id": "scene_02"}]) == {
        "scene_01": 1,
        "scene_02": 2,
    }
    assert runner._scene_index_by_id([SCENE, {"scene_id": "scene_02"}]) == (
        support.scene_index_by_id([SCENE, {"scene_id": "scene_02"}])
    )

    print("[OK] image asset ref contracts")
    print("[OK] image prompt map contracts")
    print("[OK] image asset metadata contracts")
    print("[OK] scene candidate variant contracts")
    print("[OK] mock candidate file copy contract")
    print("PASS: Step 12 image asset ref support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
