from __future__ import annotations

from typing import Any, Dict, List, Optional


class RunnerImageSelectionSupport:
    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def build_image_assets_from_selected_assets(
        self,
        *,
        run_id: str,
        image_review: Dict[str, Any],
        provider: str,
        storyboard_scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Synthesize image_assets from the user's review selections.

        When ``storyboard_scenes`` is provided, any scene that has no
        successful selected asset is emitted as an explicit
        ``status='failed'`` placeholder so ``len(assets) == scene_count``
        is preserved on disk. Without this, scenes whose per-scene
        refresh API call failed (timeout / 5xx / image provider error)
        were silently dropped from the persisted outputs — downstream
        consumers (frontend placeholder builder, render gate) then
        couldn't tell pending from permanently-failed scenes, and the
        UI showed "等待生成" for scenes that would never resolve.
        """
        selected_assets = image_review.get("selected_assets") or []

        merged_assets: List[Dict[str, Any]] = []
        completed_scene_ids: set[str] = set()

        if isinstance(selected_assets, list):
            for item in selected_assets:
                if not isinstance(item, dict):
                    continue

                selected_asset_ref = item.get("selected_asset_ref") or {}
                if not isinstance(selected_asset_ref, dict):
                    selected_asset_ref = {}

                reference_images = (
                    item.get("reference_images")
                    or selected_asset_ref.get("reference_images")
                    or []
                )
                reference_image_support = (
                    item.get("reference_image_support")
                    or selected_asset_ref.get("reference_image_support")
                    or {
                        "requested": bool(reference_images),
                        "provider_supports_reference_image": False,
                        "mode": "metadata_only",
                    }
                )

                merged_assets.append(
                    {
                        "scene_id": item.get("scene_id"),
                        "scene_title": item.get("scene_title"),
                        "characters": item.get("characters") or [],
                        "character_ids": item.get("character_ids") or [],
                        "prompt": item.get("prompt") or "",
                        "file_name": selected_asset_ref.get("file_name"),
                        "relative_path": selected_asset_ref.get("relative_path"),
                        "public_url": selected_asset_ref.get("public_url"),
                        "mime_type": selected_asset_ref.get("mime_type"),
                        "duration_sec": item.get("duration_sec")
                        or selected_asset_ref.get("duration_sec"),
                        "duration_estimate_sec": item.get("duration_estimate_sec")
                        or selected_asset_ref.get("duration_estimate_sec"),
                        "selected_asset_ref": dict(selected_asset_ref),
                        "reference_images": reference_images,
                        "reference_image_support": reference_image_support,
                        "status": "generated",
                        "candidate_asset_refs": item.get("candidate_asset_refs") or [],
                    }
                )

                scene_id = str(item.get("scene_id") or "").strip()
                if scene_id:
                    completed_scene_ids.add(scene_id)

        # Failed-scene placeholders. Only emitted when the caller passes
        # the full storyboard.scenes list — older callers (no scenes
        # arg) keep the legacy behavior so this refactor is safe to land
        # incrementally.
        failed_scene_ids: List[str] = []
        if isinstance(storyboard_scenes, list):
            for scene in storyboard_scenes:
                if not isinstance(scene, dict):
                    continue
                scene_id = str(scene.get("scene_id") or "").strip()
                if not scene_id or scene_id in completed_scene_ids:
                    continue
                scene_title = str(scene.get("scene_title") or scene_id).strip()
                merged_assets.append(
                    {
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "status": "failed",
                        "error_message": (
                            "image generation failed and was not retried"
                        ),
                        "file_name": None,
                        "relative_path": None,
                        "public_url": None,
                        "mime_type": None,
                        "selected_asset_ref": {},
                        "candidate_asset_refs": [],
                        "reference_images": [],
                    }
                )
                failed_scene_ids.append(scene_id)

        generated_count = len(merged_assets) - len(failed_scene_ids)

        return {
            "enabled": True,
            "run_id": run_id,
            "provider": str(provider or self._runner._image_provider_name()),
            "provider_capabilities": {
                "supports_reference_image": False,
                "reference_image_mode": "metadata_only",
            },
            "asset_count": len(merged_assets),
            "generated_count": generated_count,
            "failed_count": len(failed_scene_ids),
            "failed_scene_ids": failed_scene_ids,
            "assets": merged_assets,
        }
