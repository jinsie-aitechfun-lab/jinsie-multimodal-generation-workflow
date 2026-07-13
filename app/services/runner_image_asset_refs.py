from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class RunnerImageAssetRefsSupport:
    """Image asset reference and metadata helpers.

    Extracted as Step 12 of the runner refactor. These helpers normalize image
    prompt lookup maps, asset references, candidate variants, and scene/image
    metadata used by image review, image queue, and single-scene refresh paths.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def image_asset_by_scene_id(
        self, outputs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        image_assets = outputs.get("image_assets") or {}
        assets = image_assets.get("assets") or []

        mapping: Dict[str, Dict[str, Any]] = {}
        for item in assets:
            if not isinstance(item, dict):
                continue
            scene_id = str(item.get("scene_id") or "").strip()
            if scene_id:
                mapping[scene_id] = item
        return mapping

    def image_asset_ref_from_item(
        self,
        item: Dict[str, Any],
        provider: str,
    ) -> Dict[str, Any]:
        ref = {
            "scene_id": item.get("scene_id"),
            "file_name": item.get("file_name"),
            "relative_path": item.get("relative_path"),
            "public_url": item.get("public_url"),
            "mime_type": item.get("mime_type"),
            "provider": provider,
        }
        # Forward quality_tier so the frontend can flag candidates that
        # were rendered at Cinematic (the badge on 增强画质 outputs).
        # Falls through silently when the source dict doesn't carry one
        # — older candidates won't show a badge, just default tier.
        if "quality_tier" in item:
            ref["quality_tier"] = item["quality_tier"]
        return ref

    def build_mock_candidate_asset_refs(
        self,
        item: Dict[str, Any],
        provider: str,
    ) -> List[Dict[str, Any]]:
        primary_ref = self.image_asset_ref_from_item(item, provider)

        relative_path = str(item.get("relative_path") or "").strip()
        public_url = str(item.get("public_url") or "").strip()
        file_name = str(item.get("file_name") or "").strip()
        scene_id = item.get("scene_id")
        mime_type = item.get("mime_type")

        if not relative_path or not public_url or not file_name:
            return [primary_ref]

        if "." in file_name:
            file_stem, file_ext = file_name.rsplit(".", 1)
            mock_file_name = f"{file_stem}__candidate_b.{file_ext}"
        else:
            mock_file_name = f"{file_name}__candidate_b"

        if "." in relative_path:
            relative_stem, relative_ext = relative_path.rsplit(".", 1)
            mock_relative_path = f"{relative_stem}__candidate_b.{relative_ext}"
        else:
            mock_relative_path = f"{relative_path}__candidate_b"

        if "." in public_url:
            public_stem, public_ext = public_url.rsplit(".", 1)
            mock_public_url = f"{public_stem}__candidate_b.{public_ext}"
        else:
            mock_public_url = f"{public_url}__candidate_b"

        mock_ref = {
            "scene_id": scene_id,
            "file_name": mock_file_name,
            "relative_path": mock_relative_path,
            "public_url": mock_public_url,
            "mime_type": mime_type,
            "provider": f"{provider}_mock_candidate",
        }

        self.ensure_mock_candidate_asset_file(primary_ref, mock_ref)

        return [primary_ref, mock_ref]

    def ensure_mock_candidate_asset_file(
        self,
        primary_ref: Dict[str, Any],
        candidate_ref: Dict[str, Any],
    ) -> None:
        primary_relative_path = str(primary_ref.get("relative_path") or "").strip()
        candidate_relative_path = str(candidate_ref.get("relative_path") or "").strip()

        if not primary_relative_path or not candidate_relative_path:
            return

        source_path = PROJECT_ROOT / primary_relative_path
        target_path = PROJECT_ROOT / candidate_relative_path

        if not source_path.exists():
            return

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if not target_path.exists():
            shutil.copyfile(source_path, target_path)

    def scene_index_by_id(
        self,
        scenes: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        for index, scene in enumerate(scenes, start=1):
            scene_id = str(scene.get("scene_id") or "").strip()
            if scene_id:
                mapping[scene_id] = index
        return mapping

    def image_prompt_item_maps(
        self, outputs: Dict[str, Any]
    ) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        image_prompts = outputs.get("image_prompts") or {}
        prompt_items = image_prompts.get("prompts") or []

        prompt_by_scene_id: Dict[str, Dict[str, Any]] = {}
        prompt_by_shot_id: Dict[str, Dict[str, Any]] = {}

        for item in prompt_items:
            if not isinstance(item, dict):
                continue

            scene_id = str(item.get("scene_id") or "").strip()
            shot_id = str(item.get("shot_id") or "").strip()

            if scene_id:
                prompt_by_scene_id[scene_id] = item
            if shot_id:
                prompt_by_shot_id[shot_id] = item

        return prompt_by_scene_id, prompt_by_shot_id

    def image_asset_metadata(
        self,
        *,
        scene: Optional[Dict[str, Any]] = None,
        prompt_item: Optional[Dict[str, Any]] = None,
        fallback_scene_title: str = "",
    ) -> Dict[str, Any]:
        scene = scene or {}
        prompt_item = prompt_item or {}

        scene_title = str(
            prompt_item.get("scene_title")
            or scene.get("scene_title")
            or fallback_scene_title
            or ""
        ).strip()

        characters = prompt_item.get("characters")
        if not isinstance(characters, list):
            characters = scene.get("characters") or []
        if not isinstance(characters, list):
            characters = []

        prompt_text = str(prompt_item.get("prompt") or "").strip()

        return {
            "scene_title": scene_title,
            "characters": characters,
            "character_ids": self._runner._scene_characters.character_ids_from_bindings(
                characters
            ),
            "prompt": prompt_text,
        }

    def scene_candidate_variant(
        self,
        *,
        scene: Dict[str, Any],
        candidate_index: int,
    ) -> Dict[str, Any]:
        variant = dict(scene)

        scene_title = str(scene.get("scene_title") or "").strip()
        visual_description = str(scene.get("visual_description") or "").strip()
        narration = str(scene.get("narration") or "").strip()
        shot_type = str(scene.get("shot_type") or "medium").strip()

        if candidate_index == 0:
            variant["candidate_key"] = "candidate_a"
            variant["candidate_label"] = "Primary Composition"
            return variant

        variant["candidate_key"] = "candidate_b"
        variant["candidate_label"] = "Alternate Composition"

        if shot_type == "wide":
            variant["shot_type"] = "medium"
        elif shot_type == "medium":
            variant["shot_type"] = "close"
        else:
            variant["shot_type"] = "wide"

        if scene_title:
            variant["scene_title"] = f"{scene_title} Alt"

        if visual_description:
            variant["visual_description"] = (
                f"{visual_description}; alternate composition, different framing, "
                "slightly changed pose emphasis, secondary visual arrangement"
            )

        if narration:
            variant["narration"] = narration

        return variant
