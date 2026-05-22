from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.services.image_candidate_selector import select_best_candidate
from app.services.image_provider_adapter import ApiImageGeneratorAdapter
from app.services.image_provider_types import ImageGenerationTask


class RunnerSingleSceneImageSupport:
    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def run_single_scene_pillow_image_asset(
        self,
        *,
        ctx: Any,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
    ) -> Dict[str, Any]:
        prompt_by_scene_id, _ = self._runner._image_prompt_item_maps(outputs)

        run_dir = self._runner._ensure_image_run_dir(ctx.run_id)
        scene_id = str(scene.get("scene_id") or f"scene_{scene_index:02d}")
        prompt_item = prompt_by_scene_id.get(scene_id) or {}
        base_prompt = str(prompt_item.get("prompt") or "").strip()

        if not base_prompt:
            visual_description = str(scene.get("visual_description") or "").strip()
            narration = str(scene.get("narration") or "").strip()
            base_prompt = visual_description or narration or f"storybook scene {scene_id}"

        asset_meta = self._runner._image_asset_metadata(
            scene=scene,
            prompt_item=prompt_item,
            fallback_scene_title=str(scene.get("scene_title") or "").strip(),
        )

        candidate_asset_refs: List[Dict[str, Any]] = []

        for candidate_index, candidate_suffix in enumerate(["candidate_a", "candidate_b"]):
            candidate_scene = self._runner._scene_candidate_variant(
                scene=scene,
                candidate_index=candidate_index,
            )

            file_name = f"{scene_id}__{candidate_suffix}.png"
            output_path = run_dir / file_name
            output_path.parent.mkdir(parents=True, exist_ok=True)

            image_bytes = self._runner._build_scene_png(
                ctx,
                candidate_scene,
                scene_index + candidate_index,
            )
            if not isinstance(image_bytes, (bytes, bytearray)):
                raise RuntimeError(
                    f"pillow fallback returned invalid bytes for scene {scene_id} ({candidate_suffix})"
                )

            output_path.write_bytes(bytes(image_bytes))

            candidate_asset_refs.append(
                {
                    "scene_id": scene_id,
                    "file_name": file_name,
                    "relative_path": f"assets/mock/image/{ctx.run_id}/{file_name}",
                    "public_url": f"/assets/mock/image/{ctx.run_id}/{file_name}",
                    "mime_type": "image/png",
                    "provider": "pillow_storybook_renderer",
                }
            )

        primary_ref = candidate_asset_refs[0]

        return {
            "scene_id": scene_id,
            "scene_title": asset_meta["scene_title"],
            "characters": asset_meta["characters"],
            "character_ids": asset_meta["character_ids"],
            "prompt": base_prompt,
            "file_name": primary_ref["file_name"],
            "relative_path": primary_ref["relative_path"],
            "public_url": primary_ref["public_url"],
            "mime_type": primary_ref["mime_type"],
            "status": "generated",
            "candidate_asset_refs": candidate_asset_refs,
        }

    def run_single_scene_api_image_asset(
        self,
        *,
        ctx: Any,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
    ) -> Dict[str, Any]:
        runner = self._runner
        prompt_by_scene_id, _ = runner._image_prompt_item_maps(outputs)

        run_dir = runner._ensure_image_run_dir(ctx.run_id)
        scene_id = str(scene.get("scene_id") or f"scene_{scene_index:02d}")
        prompt_item = prompt_by_scene_id.get(scene_id) or {}
        base_prompt = str(prompt_item.get("prompt") or "").strip()

        if not base_prompt:
            visual_description = str(scene.get("visual_description") or "").strip()
            narration = str(scene.get("narration") or "").strip()
            base_prompt = visual_description or narration or f"storybook scene {scene_id}"

        asset_meta = runner._image_asset_metadata(
            scene=scene,
            prompt_item=prompt_item,
            fallback_scene_title=str(scene.get("scene_title") or "").strip(),
        )

        candidate_asset_refs: List[Dict[str, Any]] = []
        adapter = ApiImageGeneratorAdapter(runner)

        for candidate_index, candidate_suffix in enumerate(["candidate_a", "candidate_b"]):
            candidate_scene = runner._scene_candidate_variant(
                scene=scene,
                candidate_index=candidate_index,
            )

            candidate_prompt = base_prompt
            if candidate_index == 1:
                candidate_prompt = (
                    f"{base_prompt}, alternate composition, different framing, "
                    "slightly changed pose emphasis, secondary visual arrangement"
                )

            file_name = f"{scene_id}__{candidate_suffix}.png"
            output_path = run_dir / file_name

            task = ImageGenerationTask(
                run_id=ctx.run_id,
                item_id=scene_id,
                scene_id=scene_id,
                prompt=candidate_prompt,
                candidate_suffix=candidate_suffix,
                output_path=output_path,
                relative_path=f"assets/mock/image/{ctx.run_id}/{file_name}",
                public_url=f"/assets/mock/image/{ctx.run_id}/{file_name}",
                prompt_metadata={
                    "ctx": ctx,
                    "scene": candidate_scene,
                    "scene_index": scene_index + candidate_index,
                },
            )

            image_bytes = adapter.generate(task)
            if not isinstance(image_bytes, (bytes, bytearray)):
                raise RuntimeError(
                    f"api image provider returned invalid bytes for scene {scene_id} ({candidate_suffix})"
                )

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(bytes(image_bytes))

            candidate_asset_refs.append(
                {
                    "scene_id": scene_id,
                    "file_name": file_name,
                    "relative_path": task.relative_path,
                    "public_url": task.public_url,
                    "mime_type": "image/png",
                    "provider": "api_image_generator",
                }
            )

        selection = select_best_candidate(
            candidate_asset_refs=candidate_asset_refs,
            prompt=base_prompt,
            characters=asset_meta["characters"],
        )
        candidate_asset_refs = selection["candidate_asset_refs"]
        selected_asset_ref = selection["selected_asset_ref"]

        return {
            "scene_id": scene_id,
            "scene_title": asset_meta["scene_title"],
            "characters": asset_meta["characters"],
            "character_ids": asset_meta["character_ids"],
            "prompt": base_prompt,
            "selected_asset_ref": dict(selected_asset_ref),
            "file_name": selected_asset_ref["file_name"],
            "relative_path": selected_asset_ref["relative_path"],
            "public_url": selected_asset_ref["public_url"],
            "mime_type": selected_asset_ref["mime_type"],
            "status": "generated",
            "candidate_asset_refs": candidate_asset_refs,
            "selection_source": selection.get("selection_source"),
            "selection_reason": selection.get("selection_reason"),
            "candidate_scores": selection.get("candidate_scores") or [],
        }

    def run_single_scene_image_asset(
        self,
        *,
        ctx: Any,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
    ) -> Dict[str, Any]:
        provider = self._runner._image_provider_name()

        if provider == "pillow_storybook_renderer":
            asset = self.run_single_scene_pillow_image_asset(
                ctx=ctx,
                outputs=outputs,
                scene=scene,
                scene_index=scene_index,
            )
            return {
                "enabled": True,
                "run_id": ctx.run_id,
                "provider": "pillow_storybook_renderer",
                "asset_count": 1,
                "assets": [asset],
            }

        if provider == "api_image_generator":
            try:
                asset = self.run_single_scene_api_image_asset(
                    ctx=ctx,
                    outputs=outputs,
                    scene=scene,
                    scene_index=scene_index,
                )
                return {
                    "enabled": True,
                    "run_id": ctx.run_id,
                    "provider": "api_image_generator",
                    "asset_count": 1,
                    "assets": [asset],
                }
            except Exception as e:
                if self._runner._is_rate_limit_error(e):
                    strategy = self._runner._image_429_strategy()
                    if strategy == "pending":
                        return self._runner._build_pending_image_assets_result(
                            ctx=ctx,
                            provider="api_image_generator",
                            reason=str(e),
                            retry_after_sec=60,
                        )

                raise RuntimeError(
                    "single scene image asset generation failed with provider=api_image_generator; "
                    f"pillow fallback is disabled for API runs: {e}"
                ) from e
        
        raise RuntimeError(f"unknown image provider: {provider}")
