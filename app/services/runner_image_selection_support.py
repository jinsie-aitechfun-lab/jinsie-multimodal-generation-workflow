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
        known_failed_scene_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Synthesize image_assets from the user's review selections.

        Failed-scene placeholders are emitted ONLY for scenes whose IDs
        are explicitly listed in ``known_failed_scene_ids``. Earlier
        revisions inferred "failed" from "absence in selected_assets",
        but during bulk refresh that wrongly marked scenes still queued
        for processing as failed — counts on the FE diverged from the
        FE's own placeholder state, and the user briefly saw red 失败
        cards for scenes that would generate successfully a moment
        later. The caller is now responsible for tracking which scenes
        truly failed (after the provider+quality retry layers inside
        one /v1/image-review/refresh-scene call exhausted) and passing
        that set in.

        Not-yet-attempted scenes intentionally do NOT appear in the
        output array. The FE's placeholder builder treats missing
        scenes as 'waiting' (the workflow is still running) unless the
        workflow has terminated, in which case they degrade to failed
        via the legacy-terminal heuristic.

        ``storyboard_scenes`` is still used to look up scene titles for
        the failed-placeholder records; without it the placeholder
        falls back to scene_id as its title.
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

        # Failed-scene placeholders. Only emitted for scenes the caller
        # has *explicitly* told us failed. Scenes absent from both
        # ``selected_assets`` AND ``known_failed_scene_ids`` are treated
        # as not-yet-attempted and intentionally omitted from the output.
        failed_scene_ids: List[str] = []
        scenes_by_id: Dict[str, Dict[str, Any]] = {}
        if isinstance(storyboard_scenes, list):
            for scene in storyboard_scenes:
                if not isinstance(scene, dict):
                    continue
                sid = str(scene.get("scene_id") or "").strip()
                if sid:
                    scenes_by_id[sid] = scene

        if known_failed_scene_ids:
            for raw_id in known_failed_scene_ids:
                scene_id = str(raw_id or "").strip()
                if not scene_id:
                    continue
                if scene_id in completed_scene_ids:
                    # Caller marked it failed earlier but it has since
                    # succeeded (e.g. retry-then-success) — selected_assets
                    # wins, no failure placeholder.
                    continue
                scene = scenes_by_id.get(scene_id, {})
                scene_title = str(scene.get("scene_title") or scene_id).strip()
                merged_assets.append(
                    {
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "status": "failed",
                        "error_message": (
                            "image generation failed after all retries"
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
