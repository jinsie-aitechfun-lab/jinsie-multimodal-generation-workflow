from __future__ import annotations

from typing import Any, Dict, List

from app.services.image_provider_adapter import (
    ApiImageGeneratorAdapter,
    PillowStorybookAdapter,
)
from app.services.image_provider_retry import is_rate_limit_error
from app.services.image_provider_types import (
    PROVIDER_API,
    PROVIDER_PILLOW,
    ImageGenerationTask,
    QueueExecutionResult,
    QueuePolicy,
)


class ImageProviderQueue:
    def __init__(self, runner: Any) -> None:
        self._runner = runner
        self._adapters = {
            PROVIDER_PILLOW: PillowStorybookAdapter(runner),
            PROVIDER_API: ApiImageGeneratorAdapter(runner),
        }

    def run(
        self,
        *,
        ctx: Any,
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        policy = QueuePolicy(
            primary_provider=self._runner._image_provider_name(),
            fallback_provider=self._runner._image_fallback_provider_name(),
            fallback_enabled=self._runner._api_image_fallback_to_pillow(),
            rate_limit_strategy=self._runner._image_429_strategy(),
        )

        try:
            result = self._run_provider(
                provider=policy.primary_provider,
                ctx=ctx,
                outputs=outputs,
            )
            return self._to_output_dict(result, ctx=ctx)
        except Exception as error:
            if (
                policy.primary_provider == PROVIDER_API
                and policy.rate_limit_strategy == "pending"
                and is_rate_limit_error(error)
            ):
                return self._runner._build_pending_image_assets_result(
                    ctx=ctx,
                    provider=PROVIDER_API,
                    reason=str(error),
                    retry_after_sec=60,
                )

            if (
                policy.primary_provider == PROVIDER_API
                and policy.fallback_enabled
                and policy.fallback_provider == PROVIDER_PILLOW
            ):
                fallback_result = self._run_provider(
                    provider=PROVIDER_PILLOW,
                    ctx=ctx,
                    outputs=outputs,
                )
                fallback_output = self._to_output_dict(fallback_result, ctx=ctx)
                fallback_output["fallback"] = {
                    "from_provider": PROVIDER_API,
                    "to_provider": PROVIDER_PILLOW,
                    "reason": str(error),
                }
                return fallback_output

            raise RuntimeError(
                f"image asset generation failed with provider={policy.primary_provider}: {error}"
            ) from error

    def _run_provider(
        self,
        *,
        provider: str,
        ctx: Any,
        outputs: Dict[str, Any],
    ) -> QueueExecutionResult:
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        scene_by_id = {
            str(scene.get("scene_id")): scene
            for scene in scenes
            if scene.get("scene_id")
        }

        prompt_by_scene_id, prompt_by_shot_id = self._runner._image_prompt_item_maps(outputs)
        run_dir = self._runner._ensure_image_run_dir(ctx.run_id)
        assets: List[Dict[str, Any]] = []

        if shot_items:
            for index, shot in enumerate(shot_items, start=1):
                shot_id = str(shot.get("shot_id") or f"shot_{index:02d}")
                scene_id = str(shot.get("scene_id") or "").strip()
                scene_title = str(shot.get("scene_title") or f"Shot {index}").strip()
                visual_description = str(shot.get("visual_description") or "").strip()
                shot_text = str(shot.get("text") or "").strip()
                shot_type = str(shot.get("shot_type") or "medium").strip()
                transition = str(shot.get("transition") or "fade").strip()

                parent_scene = scene_by_id.get(scene_id) or {}
                prompt_item = (
                    prompt_by_shot_id.get(shot_id)
                    or prompt_by_scene_id.get(scene_id)
                    or {}
                )
                base_prompt = str(prompt_item.get("prompt") or "").strip()
                if not base_prompt:
                    base_prompt = visual_description or shot_text or f"storybook shot {shot_id}"

                asset_meta = self._runner._image_asset_metadata(
                    scene=scene_by_id.get(scene_id) or {},
                    prompt_item=prompt_item,
                    fallback_scene_title=scene_title,
                )

                candidate_asset_refs = self._generate_shot_candidates(
                    provider=provider,
                    ctx=ctx,
                    run_dir=run_dir,
                    index=index,
                    shot=shot,
                    shot_id=shot_id,
                    scene_id=scene_id,
                    scene_title=scene_title,
                    base_prompt=base_prompt,
                    prompt_item=prompt_item,
                    parent_scene=parent_scene,
                    shot_type=shot_type,
                    transition=transition,
                )

                primary_ref = candidate_asset_refs[0]
                assets.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": asset_meta["scene_title"],
                        "characters": asset_meta["characters"],
                        "character_ids": asset_meta["character_ids"],
                        "prompt": base_prompt,
                        "selected_asset_ref": dict(primary_ref),
                        "file_name": primary_ref["file_name"],
                        "relative_path": primary_ref["relative_path"],
                        "public_url": primary_ref["public_url"],
                        "mime_type": primary_ref["mime_type"],
                        "status": "generated",
                        "candidate_asset_refs": candidate_asset_refs,
                    }
                )
        else:
            for index, scene in enumerate(scenes, start=1):
                scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
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

                candidate_asset_refs = self._generate_scene_candidates(
                    provider=provider,
                    ctx=ctx,
                    run_dir=run_dir,
                    index=index,
                    scene=scene,
                    scene_id=scene_id,
                    base_prompt=base_prompt,
                )

                primary_ref = candidate_asset_refs[0]
                assets.append(
                    {
                        "scene_id": scene_id,
                        "scene_title": asset_meta["scene_title"],
                        "characters": asset_meta["characters"],
                        "character_ids": asset_meta["character_ids"],
                        "prompt": base_prompt,
                        "selected_asset_ref": dict(primary_ref),
                        "file_name": primary_ref["file_name"],
                        "relative_path": primary_ref["relative_path"],
                        "public_url": primary_ref["public_url"],
                        "mime_type": primary_ref["mime_type"],
                        "status": "generated",
                        "candidate_asset_refs": candidate_asset_refs,
                    }
                )

        return QueueExecutionResult(
            status="generated",
            provider=provider,
            assets=assets,
        )

    def _generate_shot_candidates(
        self,
        *,
        provider: str,
        ctx: Any,
        run_dir: Any,
        index: int,
        shot: Dict[str, Any],
        shot_id: str,
        scene_id: str,
        scene_title: str,
        base_prompt: str,
        prompt_item: Dict[str, Any],
        parent_scene: Dict[str, Any],
        shot_type: str,
        transition: str,
    ) -> List[Dict[str, Any]]:
        candidate_asset_refs: List[Dict[str, Any]] = []

        for candidate_index, candidate_suffix in enumerate(["candidate_a", "candidate_b"]):
            candidate_prompt = base_prompt
            if candidate_index == 1:
                candidate_prompt = (
                    f"{base_prompt}, alternate composition, different framing, "
                    "slightly changed pose emphasis, secondary visual arrangement"
                )

            candidate_scene = {
                "scene_id": shot_id,
                "scene_title": scene_title,
                "visual_description": str(shot.get("visual_description") or "").strip(),
                "narration": str(shot.get("text") or "").strip(),
                "duration_sec": 0,
                "shot_type": shot_type,
                "transition": transition,
                "characters": (
                    prompt_item.get("characters")
                    or parent_scene.get("characters")
                    or []
                ),
                "candidate_key": candidate_suffix,
                "candidate_label": (
                    "Primary Composition"
                    if candidate_index == 0
                    else "Alternate Composition"
                ),
            }

            file_name = f"{shot_id}__{candidate_suffix}.png"
            output_path = run_dir / file_name

            task = ImageGenerationTask(
                run_id=ctx.run_id,
                item_id=shot_id,
                scene_id=scene_id,
                prompt=candidate_prompt,
                candidate_suffix=candidate_suffix,
                output_path=output_path,
                relative_path=f"assets/mock/image/{ctx.run_id}/{file_name}",
                public_url=f"/assets/mock/image/{ctx.run_id}/{file_name}",
                prompt_metadata={
                    "ctx": ctx,
                    "scene": candidate_scene,
                    "scene_index": index + candidate_index,
                },
            )

            image_bytes = self._generate_candidate_bytes(provider=provider, task=task)
            output_path.write_bytes(bytes(image_bytes))

            candidate_asset_refs.append(
                {
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "file_name": file_name,
                    "relative_path": task.relative_path,
                    "public_url": task.public_url,
                    "mime_type": "image/png",
                    "provider": provider,
                }
            )

        # throttle between scenes to avoid IPM limit
        if provider == PROVIDER_API:
            import time
            time.sleep(3)
        return candidate_asset_refs

    def _generate_scene_candidates(
        self,
        *,
        provider: str,
        ctx: Any,
        run_dir: Any,
        index: int,
        scene: Dict[str, Any],
        scene_id: str,
        base_prompt: str,
    ) -> List[Dict[str, Any]]:
        candidate_asset_refs: List[Dict[str, Any]] = []

        for candidate_index, candidate_suffix in enumerate(["candidate_a", "candidate_b"]):
            candidate_scene = self._runner._scene_candidate_variant(
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
                    "scene_index": index + candidate_index,
                },
            )

            image_bytes = self._generate_candidate_bytes(provider=provider, task=task)
            output_path.write_bytes(bytes(image_bytes))

            candidate_asset_refs.append(
                {
                    "scene_id": scene_id,
                    "file_name": file_name,
                    "relative_path": task.relative_path,
                    "public_url": task.public_url,
                    "mime_type": "image/png",
                    "provider": provider,
                }
            )

        return candidate_asset_refs

    def _generate_candidate_bytes(
        self,
        *,
        provider: str,
        task: ImageGenerationTask,
    ) -> bytes:
        adapter = self._adapters.get(provider)
        if adapter is None:
            raise RuntimeError(f"unknown image provider: {provider}")

        image_bytes = adapter.generate(task)
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise RuntimeError(
                f"image provider returned invalid bytes for item {task.item_id} ({task.candidate_suffix})"
            )
        return bytes(image_bytes)

    def _to_output_dict(
        self,
        result: QueueExecutionResult,
        *,
        ctx: Any,
    ) -> Dict[str, Any]:
        return {
            "enabled": True,
            "run_id": ctx.run_id,
            "provider": result.provider,
            "asset_count": len(result.assets),
            "assets": result.assets,
        }