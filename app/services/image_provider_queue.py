from __future__ import annotations

from typing import Any, Dict, List

from app.services.image_provider_adapter import (
    ApiImageGeneratorAdapter,
    PillowStorybookAdapter,
)
from app.services.image_provider_retry import is_rate_limit_error
from app.services.image_candidate_selector import select_best_candidate
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
                raise RuntimeError(
                    "api image generation failed and pillow fallback is disabled for final generation: "
                    f"{error}"
                ) from error

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
        character_anchor = self._generate_character_anchor_reference(
            provider=provider,
            ctx=ctx,
            run_dir=run_dir,
            outputs=outputs,
        )
        anchor_reference_images = character_anchor.get("reference_images") or []
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
                    anchor_reference_images=anchor_reference_images,
                )

                selection = select_best_candidate(
                    candidate_asset_refs=candidate_asset_refs,
                    prompt=base_prompt,
                    characters=asset_meta["characters"],
                )
                candidate_asset_refs = selection["candidate_asset_refs"]
                selected_asset_ref = selection["selected_asset_ref"]

                if selection.get("should_retry"):
                    retry_candidate_asset_refs = self._generate_shot_candidates(
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
                        anchor_reference_images=anchor_reference_images,
                    )
                    retry_selection = select_best_candidate(
                        candidate_asset_refs=retry_candidate_asset_refs,
                        prompt=base_prompt,
                        characters=asset_meta["characters"],
                    )
                    if retry_selection.get("best_score", -1.0) >= selection.get("best_score", -1.0):
                        selection = retry_selection
                        candidate_asset_refs = retry_selection["candidate_asset_refs"]
                        selected_asset_ref = retry_selection["selected_asset_ref"]

                assets.append(
                    {
                        "shot_id": shot_id,
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
                        "duration_sec": selected_asset_ref.get("duration_sec"),
                        "duration_estimate_sec": selected_asset_ref.get("duration_estimate_sec"),
                        "status": "generated",
                        "reference_images": selected_asset_ref.get("reference_images") or [],
                        "reference_image_support": selected_asset_ref.get("reference_image_support")
                        or {
                            "requested": bool(selected_asset_ref.get("reference_images") or []),
                            "provider_supports_reference_image": False,
                            "mode": "metadata_only",
                        },
                        "candidate_asset_refs": candidate_asset_refs,
                        "selection_source": selection.get("selection_source"),
                        "selection_reason": selection.get("selection_reason"),
                        "candidate_scores": selection.get("candidate_scores") or [],
                        "quality_gates": selection.get("quality_gates") or {},
                        "review_required": bool(selection.get("review_required")),
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
                    prompt_item=prompt_item,
                    anchor_reference_images=anchor_reference_images,
                )

                selection = select_best_candidate(
                    candidate_asset_refs=candidate_asset_refs,
                    prompt=base_prompt,
                    characters=asset_meta["characters"],
                )
                candidate_asset_refs = selection["candidate_asset_refs"]
                selected_asset_ref = selection["selected_asset_ref"]

                if selection.get("should_retry"):
                    retry_candidate_asset_refs = self._generate_scene_candidates(
                        provider=provider,
                        ctx=ctx,
                        run_dir=run_dir,
                        index=index,
                        scene=scene,
                        scene_id=scene_id,
                        base_prompt=base_prompt,
                        prompt_item=prompt_item,
                        anchor_reference_images=anchor_reference_images,
                    )
                    retry_selection = select_best_candidate(
                        candidate_asset_refs=retry_candidate_asset_refs,
                        prompt=base_prompt,
                        characters=asset_meta["characters"],
                    )
                    if retry_selection.get("best_score", -1.0) >= selection.get("best_score", -1.0):
                        selection = retry_selection
                        candidate_asset_refs = retry_selection["candidate_asset_refs"]
                        selected_asset_ref = retry_selection["selected_asset_ref"]

                assets.append(
                    {
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
                        "duration_sec": selected_asset_ref.get("duration_sec"),
                        "duration_estimate_sec": selected_asset_ref.get("duration_estimate_sec"),
                        "status": "generated",
                        "reference_images": selected_asset_ref.get("reference_images") or [],
                        "reference_image_support": selected_asset_ref.get("reference_image_support")
                        or {
                            "requested": bool(selected_asset_ref.get("reference_images") or []),
                            "provider_supports_reference_image": False,
                            "mode": "metadata_only",
                        },
                        "candidate_asset_refs": candidate_asset_refs,
                        "selection_source": selection.get("selection_source"),
                        "selection_reason": selection.get("selection_reason"),
                        "candidate_scores": selection.get("candidate_scores") or [],
                        "quality_gates": selection.get("quality_gates") or {},
                        "review_required": bool(selection.get("review_required")),
                    }
                )

        return QueueExecutionResult(
            status="generated",
            provider=provider,
            assets=assets,
            character_anchor=character_anchor,
        )

    def _build_character_anchor_prompt(
        self,
        outputs: Dict[str, Any],
    ) -> str:
        image_prompts = outputs.get("image_prompts") or {}
        profile = image_prompts.get("character_visual_profile") or {}
        anchor = image_prompts.get("character_anchor") or {}

        subject = str(
            anchor.get("subject")
            or profile.get("subject")
            or "main storybook character"
        ).strip()
        visual_identity = str(profile.get("visual_identity") or "").strip()
        must_keep = profile.get("must_keep") or []
        must_avoid = profile.get("must_avoid") or []

        keep_text = ", ".join(str(item).strip() for item in must_keep if str(item).strip())
        avoid_text = ", ".join(str(item).strip() for item in must_avoid if str(item).strip())

        parts = [
            "character reference sheet",
            f"single centered full-body design of {subject}",
            "plain clean light background",
            "no story scene, no extra characters, no props unless part of the fixed character identity",
            "front-facing or three-quarter view, clear silhouette, stable reusable design",
            f"fixed visual identity: {visual_identity}" if visual_identity else "",
            f"must keep exactly: {keep_text}" if keep_text else "",
            f"must avoid: {avoid_text}" if avoid_text else "",
            "children's storybook illustration style, soft pastel palette, clean composition",
        ]

        return "; ".join(part for part in parts if part)


    def _generate_character_anchor_reference(
        self,
        *,
        provider: str,
        ctx: Any,
        run_dir: Any,
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        image_prompts = outputs.get("image_prompts") or {}
        anchor = image_prompts.get("character_anchor") or {}

        if not isinstance(anchor, dict) or not anchor.get("enabled"):
            return {
                "enabled": False,
                "mode": "disabled",
                "reference_images": [],
            }

        subject = str(anchor.get("subject") or "main_subject").strip() or "main_subject"
        anchor_prompt = self._build_character_anchor_prompt(outputs)

        anchor_dir = run_dir / "character_anchor"
        file_name = "main_subject.png"
        output_path = anchor_dir / file_name

        relative_path = f"assets/mock/image/{ctx.run_id}/character_anchor/{file_name}"
        public_url = f"/assets/mock/image/{ctx.run_id}/character_anchor/{file_name}"

        anchor_scene = {
            "scene_id": "character_anchor",
            "scene_title": "Character Anchor",
            "visual_description": anchor_prompt,
            "narration": "",
            "duration_sec": 0,
            "characters": [],
        }

        task = ImageGenerationTask(
            run_id=ctx.run_id,
            item_id="character_anchor",
            scene_id="character_anchor",
            prompt=anchor_prompt,
            candidate_suffix="main_subject",
            output_path=output_path,
            relative_path=relative_path,
            public_url=public_url,
            reference_images=[],
            prompt_metadata={
                "ctx": ctx,
                "scene": anchor_scene,
                "scene_index": 1,
                "character_anchor": anchor,
                "reference_images": [],
            },
        )

        image_bytes = self._generate_candidate_bytes(provider=provider, task=task)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bytes(image_bytes))

        reference_image = {
            "role": "main_subject",
            "subject": subject,
            "file_name": file_name,
            "relative_path": relative_path,
            "public_url": public_url,
            "mime_type": "image/png",
            "provider": provider,
            "source": "generated_character_anchor",
        }

        return {
            **anchor,
            "enabled": True,
            "mode": "image_reference_anchor",
            "anchor_type": "character_reference_anchor",
            "anchor_prompt": anchor_prompt,
            "reference_image": reference_image,
            "reference_images": [reference_image],
            "provider_reference_support": {
                "requested": True,
                "provider_supports_reference_image": False,
                "mode": "metadata_only",
                "reason": (
                    "character anchor image is generated and attached as metadata; "
                    "current provider adapter does not consume reference images yet"
                ),
            },
        }


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
        anchor_reference_images: List[Dict[str, Any]],
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

            reference_images = (
                prompt_item.get("reference_images")
                or (prompt_item.get("character_anchor") or {}).get("reference_images")
                or anchor_reference_images
                or []
            )
            character_anchor = prompt_item.get("character_anchor") or {}

            task = ImageGenerationTask(
                run_id=ctx.run_id,
                item_id=shot_id,
                scene_id=scene_id,
                prompt=candidate_prompt,
                candidate_suffix=candidate_suffix,
                output_path=output_path,
                relative_path=f"assets/mock/image/{ctx.run_id}/{file_name}",
                public_url=f"/assets/mock/image/{ctx.run_id}/{file_name}",
                reference_images=reference_images,
                prompt_metadata={
                    "ctx": ctx,
                    "scene": candidate_scene,
                    "scene_index": index + candidate_index,
                    "character_anchor": character_anchor,
                    "reference_images": reference_images,
                },
            )

            image_bytes = self._generate_candidate_bytes(provider=provider, task=task)
            output_path.parent.mkdir(parents=True, exist_ok=True)
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
                    "duration_sec": candidate_scene.get("duration_sec"),
                    "duration_estimate_sec": candidate_scene.get("duration_estimate_sec"),
                    "reference_images": task.reference_images,
                    "reference_image_support": {
                        "requested": bool(task.reference_images),
                        "provider_supports_reference_image": False,
                        "mode": "metadata_only",
                    },
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
        prompt_item: Dict[str, Any],
        anchor_reference_images: List[Dict[str, Any]],
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

            reference_images = (
                prompt_item.get("reference_images")
                or (prompt_item.get("character_anchor") or {}).get("reference_images")
                or anchor_reference_images
                or []
            )
            character_anchor = prompt_item.get("character_anchor") or {}

            task = ImageGenerationTask(
                run_id=ctx.run_id,
                item_id=scene_id,
                scene_id=scene_id,
                prompt=candidate_prompt,
                candidate_suffix=candidate_suffix,
                output_path=output_path,
                relative_path=f"assets/mock/image/{ctx.run_id}/{file_name}",
                public_url=f"/assets/mock/image/{ctx.run_id}/{file_name}",
                reference_images=reference_images,
                prompt_metadata={
                    "ctx": ctx,
                    "scene": candidate_scene,
                    "scene_index": index + candidate_index,
                    "character_anchor": character_anchor,
                    "reference_images": reference_images,
                },
            )

            image_bytes = self._generate_candidate_bytes(provider=provider, task=task)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(bytes(image_bytes))

            candidate_asset_refs.append(
                {
                    "scene_id": scene_id,
                    "file_name": file_name,
                    "relative_path": task.relative_path,
                    "public_url": task.public_url,
                    "mime_type": "image/png",
                    "provider": provider,
                    "duration_sec": candidate_scene.get("duration_sec"),
                    "duration_estimate_sec": candidate_scene.get("duration_estimate_sec"),
                    "reference_images": task.reference_images,
                    "reference_image_support": {
                        "requested": bool(task.reference_images),
                        "provider_supports_reference_image": False,
                        "mode": "metadata_only",
                    },
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
            "provider_capabilities": {
                "supports_reference_image": False,
                "reference_image_mode": "metadata_only",
            },
            "character_anchor": result.character_anchor,
            "asset_count": len(result.assets),
            "assets": result.assets,
        }
