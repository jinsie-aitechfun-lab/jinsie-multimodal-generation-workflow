from __future__ import annotations

from typing import Any, Dict, List


class RunnerImageReviewSupport:
    """Builders and utilities for the image_review payload.

    Extracted from WorkflowRunner as Step 2 of the runner refactor.
    All methods are pure data transformations on dict payloads;
    two of them (build_deferred_image_assets_output,
    build_image_review_from_assets, build_image_review_item_from_asset)
    delegate to the parent runner for provider-name and asset-ref
    helpers via self._runner, mirroring the pattern used by
    RunnerImageSelectionSupport.

    Behavior must remain byte-for-byte identical to the original
    methods in runner.py.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def build_deferred_image_assets_output(self, ctx: Any) -> Dict[str, Any]:
        return {
            "enabled": False,
            "run_id": ctx.run_id,
            "provider": self._runner._image_provider_name(),
            "provider_capabilities": {
                "supports_reference_image": False,
                "reference_image_mode": "metadata_only",
            },
            "status": "pending",
            "reason": "deferred_to_refresh",
            "detail": "image asset generation is deferred to /v1/image-review/refresh",
            "asset_count": 0,
            "assets": [],
        }

    def build_pending_image_review(
        self,
        *,
        reason: str = "waiting_for_image_assets",
    ) -> Dict[str, Any]:
        return {
            "enabled": False,
            "status": "pending",
            "reason": reason,
            "selected_assets": [],
        }

    def build_image_review_from_assets(
        self,
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        image_assets_output = outputs.get("image_assets") or {}
        assets = image_assets_output.get("assets") or []
        provider = str(image_assets_output.get("provider") or "").strip()

        selected_assets: List[Dict[str, Any]] = []

        for item in assets:
            if not isinstance(item, dict):
                continue

            scene_id = str(item.get("scene_id") or "").strip()
            if not scene_id:
                continue

            scene_title = str(item.get("scene_title") or "").strip()
            candidate_asset_refs = item.get("candidate_asset_refs") or []
            if not isinstance(candidate_asset_refs, list) or not candidate_asset_refs:
                candidate_asset_refs = [
                    self._runner._image_asset_ref_from_item(item, provider)
                ]

            selected_asset_ref = item.get("selected_asset_ref") or candidate_asset_refs[0]
            selection_source = (
                str(item.get("selection_source") or "").strip()
                or "default_auto_selection"
            )
            selection_reason = (
                str(item.get("selection_reason") or "").strip()
                or "default_selected_from_image_assets"
            )
            candidate_scores = item.get("candidate_scores") or []

            selected_assets.append(
                {
                    "scene_id": scene_id,
                    "scene_title": scene_title,
                    "review_status": "auto_selected",
                    "selection_mode": (
                        "auto_filter"
                        if selection_source == "auto_filter"
                        else "default_first_pass"
                    ),
                    "selection_source": selection_source,
                    "selection_reason": selection_reason,
                    "selected_asset_ref": selected_asset_ref,
                    "candidate_asset_refs": candidate_asset_refs,
                    "candidate_scores": candidate_scores,
                    "characters": item.get("characters") or [],
                    "character_ids": item.get("character_ids") or [],
                    "prompt": str(item.get("prompt") or "").strip(),
                }
            )

        return {
            "enabled": True,
            "mode": "selection_contract",
            "provider": provider,
            "asset_count": len(assets),
            "selected_count": len(selected_assets),
            "selected_assets": selected_assets,
        }

    def selection_item_by_scene_id(
        self, outputs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        image_review = outputs.get("image_review") or {}
        selected_assets = image_review.get("selected_assets") or []

        mapping: Dict[str, Dict[str, Any]] = {}
        for item in selected_assets:
            if not isinstance(item, dict):
                continue

            scene_id = str(item.get("scene_id") or "").strip()
            if scene_id:
                mapping[scene_id] = item

        return mapping

    def selected_asset_ref_by_scene_id(
        self, outputs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        selection_items = self.selection_item_by_scene_id(outputs)

        mapping: Dict[str, Dict[str, Any]] = {}
        for scene_id, item in selection_items.items():
            selected_asset_ref = item.get("selected_asset_ref") or {}
            if isinstance(selected_asset_ref, dict) and selected_asset_ref:
                mapping[scene_id] = selected_asset_ref

        return mapping

    def build_default_image_review(
        self,
        image_assets_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.build_image_review_from_assets(
            {"image_assets": image_assets_output}
        )

    def build_image_review_item_from_asset(
        self,
        asset: Dict[str, Any],
        provider: str,
    ) -> Dict[str, Any]:
        scene_id = str(asset.get("scene_id") or "").strip()
        scene_title = str(asset.get("scene_title") or "").strip()

        candidate_asset_refs = asset.get("candidate_asset_refs") or []
        if not isinstance(candidate_asset_refs, list) or not candidate_asset_refs:
            candidate_asset_refs = [
                self._runner._image_asset_ref_from_item(asset, provider)
            ]

        selected_asset_ref = asset.get("selected_asset_ref") or (
            candidate_asset_refs[0] if candidate_asset_refs else {}
        )
        selection_source = (
            str(asset.get("selection_source") or "").strip()
            or "default_auto_selection"
        )
        selection_reason = (
            str(asset.get("selection_reason") or "").strip()
            or "default_selected_from_image_assets"
        )
        candidate_scores = asset.get("candidate_scores") or []

        return {
            "scene_id": scene_id,
            "scene_title": scene_title,
            "review_status": "auto_selected",
            "selection_mode": (
                "auto_filter"
                if selection_source == "auto_filter"
                else "default_first_pass"
            ),
            "selection_source": selection_source,
            "selection_reason": selection_reason,
            "selected_asset_ref": selected_asset_ref,
            "candidate_asset_refs": candidate_asset_refs,
            "candidate_scores": candidate_scores,
            "characters": asset.get("characters") or [],
            "character_ids": asset.get("character_ids") or [],
            "prompt": str(asset.get("prompt") or "").strip(),
        }

    def upsert_image_review_item(
        self,
        image_review: Dict[str, Any],
        scene_review_item: Dict[str, Any],
        provider: str,
    ) -> Dict[str, Any]:
        updated_review = dict(image_review or {})
        selected_assets = updated_review.get("selected_assets") or []

        if not isinstance(selected_assets, list):
            selected_assets = []

        target_scene_id = str(scene_review_item.get("scene_id") or "").strip()
        if not target_scene_id:
            raise ValueError("scene_review_item.scene_id is required")

        updated_items: List[Dict[str, Any]] = []
        replaced = False

        for item in selected_assets:
            if not isinstance(item, dict):
                continue

            item_scene_id = str(item.get("scene_id") or "").strip()
            if item_scene_id == target_scene_id:
                updated_items.append(dict(scene_review_item))
                replaced = True
            else:
                updated_items.append(dict(item))

        if not replaced:
            updated_items.append(dict(scene_review_item))

        updated_review["enabled"] = True
        updated_review["mode"] = "selection_contract"
        updated_review["provider"] = provider
        updated_review["selected_assets"] = updated_items
        updated_review["selected_count"] = len(updated_items)
        updated_review["asset_count"] = len(updated_items)

        return updated_review
