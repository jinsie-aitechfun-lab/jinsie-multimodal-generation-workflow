from __future__ import annotations

from typing import Any, Dict, List


class RunnerImageSelectionSupport:
    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def build_image_assets_from_selected_assets(
        self,
        *,
        run_id: str,
        image_review: Dict[str, Any],
        provider: str,
    ) -> Dict[str, Any]:
        selected_assets = image_review.get("selected_assets") or []

        merged_assets: List[Dict[str, Any]] = []
        if isinstance(selected_assets, list):
            for item in selected_assets:
                if not isinstance(item, dict):
                    continue

                selected_asset_ref = item.get("selected_asset_ref") or {}
                if not isinstance(selected_asset_ref, dict):
                    selected_asset_ref = {}

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
                        "status": "generated",
                        "candidate_asset_refs": item.get("candidate_asset_refs") or [],
                    }
                )

        return {
            "enabled": True,
            "run_id": run_id,
            "provider": str(provider or self._runner._image_provider_name()),
            "asset_count": len(merged_assets),
            "assets": merged_assets,
        }