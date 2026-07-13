from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from app.services.image_candidate_selector import select_best_candidate
from app.services.image_provider_adapter import ApiImageGeneratorAdapter
from app.services.image_provider_types import ImageGenerationTask
from app.services.image_quality_retry_policy import (
    derive_retry_prompt_amendment,
    quality_max_retries,
    summarize_selection_for_history,
)
from app.services.runner_image_prompts_support import ensure_multi_character_anchor


class RunnerSingleSceneImageSupport:
    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def scene_negative_prompt_from_characters(
        self,
        characters: List[Dict[str, Any]],
    ) -> str:
        family_text = " ".join(
            " ".join(
                [
                    str(character.get("display_name") or ""),
                    str(character.get("species") or ""),
                    str(character.get("visual_identity") or ""),
                ]
            )
            for character in characters
            if isinstance(character, dict)
        ).lower()
        has_rabbit = any(keyword in family_text for keyword in ["rabbit", "bunny", "兔"])
        has_turtle = any(
            keyword in family_text for keyword in ["turtle", "tortoise", "乌龟", "海龟", "龟"]
        )
        has_tadpole = any(keyword in family_text for keyword in ["tadpole", "蝌蚪"])

        negatives: List[str] = [
            "hybrid rabbit turtle creature",
            "rabbit with turtle shell",
            "rabbit wearing turtle shell",
            "shell on rabbit body",
            "turtle with rabbit ears",
            "turtle with bunny ears",
            "turtle with long upright ears",
            "turtle with external ears",
            "mixed animal anatomy",
            "merged characters",
            "one body containing multiple characters",
            "missing required character",
            "solo portrait when multiple characters are required",
            "malformed animal anatomy",
            "unclear character species",
        ]

        if has_tadpole:
            negatives += [
                "adult frog",
                "frog with four legs",
                "fully grown frog",
                "frog body",
                "amphibian with limbs",
                "no tail frog",
            ]

        for character in characters:
            if not isinstance(character, dict):
                continue

            forbidden_traits = character.get("forbidden_traits") or []
            if isinstance(forbidden_traits, str):
                forbidden_traits = [
                    item.strip()
                    for item in forbidden_traits.replace("；", ",")
                    .replace(";", ",")
                    .split(",")
                    if item.strip()
                ]

            if isinstance(forbidden_traits, list):
                for item in forbidden_traits:
                    value = str(item or "").strip()
                    lowered = value.lower()
                    conflicts_with_required_rabbit = has_rabbit and (
                        "rabbit ear" in lowered
                        or "bunny ear" in lowered
                        or "upright ear" in lowered
                        or "external ear" in lowered
                        or "rabbit tail" in lowered
                        or "rabbit body" in lowered
                        or "rabbit fur" in lowered
                    )
                    conflicts_with_required_turtle = has_turtle and (
                        "turtle shell" in lowered
                        or "hard round shell" in lowered
                        or "turtle body" in lowered
                        or "turtle leg" in lowered
                        or "turtle skin" in lowered
                    )
                    if value and not (
                        conflicts_with_required_rabbit
                        or conflicts_with_required_turtle
                    ):
                        negatives.append(value)

        deduped: List[str] = []
        seen = set()
        for item in negatives:
            value = str(item or "").strip()
            if value and value not in seen:
                deduped.append(value)
                seen.add(value)

        return ", ".join(deduped)

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

        # Last-mile multi-character guard: if the scene has 2+ required
        # characters but base_prompt lacks the anti-mirror anchor (most
        # commonly because outputs["image_prompts"] was missing this
        # scene_id and we fell back to bare visual_description), prepend
        # the roster block so the diffusion model still gets the
        # "two different species, not two X, not two Y" signal.
        base_prompt = ensure_multi_character_anchor(
            base_prompt,
            asset_meta.get("characters") or [],
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
        preserve_seed: bool = False,
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
        # Last-mile multi-character guard — same purpose as the pillow
        # branch above. Critical here because the API path drives
        # generation for the real image-provider integration.
        base_prompt = ensure_multi_character_anchor(
            base_prompt,
            asset_meta.get("characters") or [],
        )
        negative_prompt = self.scene_negative_prompt_from_characters(
            asset_meta["characters"]
        )

        adapter = ApiImageGeneratorAdapter(runner)

        def _generate_candidate_pair(
            active_prompt: str,
            active_negative: str,
        ) -> List[Dict[str, Any]]:
            candidates: List[Dict[str, Any]] = []
            for candidate_index, candidate_suffix in enumerate(
                ["candidate_a", "candidate_b"]
            ):
                candidate_scene = runner._scene_candidate_variant(
                    scene=scene,
                    candidate_index=candidate_index,
                )

                candidate_prompt = active_prompt
                if candidate_index == 1:
                    candidate_prompt = (
                        f"{active_prompt}, alternate composition, different framing, "
                        "slightly changed pose emphasis, secondary visual arrangement"
                    )

                file_name = f"{scene_id}__{candidate_suffix}.png"
                output_path = run_dir / file_name

                # seed_jitter unique per request: time.time_ns() guarantees
                # two consecutive regen requests draw from different seeds,
                # so the diffusion model produces visibly different output.
                # Without this, (run_id, scene_index) is the same on every
                # retry → same seed → byte-identical image → user sees no
                # change after clicking "重新生成".
                #
                # `preserve_seed=True` (used by 增强画质) deliberately
                # SKIPS the time-based jitter so the diffusion seed
                # matches what produced the candidate on disk → same
                # composition, only the higher quality_tier (Cinematic)
                # changes the rendered detail. That's the difference
                # between "enhance the same image" and "re-roll":
                # 增强画质 keeps the picture, 重新生成 rolls fresh.
                if preserve_seed:
                    # Match the bulk-generation seed exactly: bulk path passes
                    # no seed_jitter at all (defaults to 0 for both A and B —
                    # A/B already diverge via scene_index+candidate_index).
                    seed_jitter = 0
                else:
                    seed_jitter = time.time_ns() % 10_000_000_000 + candidate_index * 7919
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
                        "negative_prompt": active_negative,
                        "quality_tier": str(getattr(ctx.input, "quality_tier", "quality") or "quality"),
                        "seed_jitter": seed_jitter,
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

                candidates.append(
                    {
                        "scene_id": scene_id,
                        "file_name": file_name,
                        "relative_path": task.relative_path,
                        "public_url": task.public_url,
                        "mime_type": "image/png",
                        "provider": "api_image_generator",
                        "negative_prompt": active_negative,
                        # Persist the quality tier so the frontend can show
                        # a "✦" badge on candidates rendered at Cinematic.
                        # This is what tells the user "this candidate was
                        # produced by 增强画质" vs a default-tier roll.
                        "quality_tier": str(
                            getattr(ctx.input, "quality_tier", "quality") or "quality"
                        ),
                    }
                )
            return candidates

        # === Attempt 1: original prompt ===
        active_prompt = base_prompt
        active_negative = negative_prompt
        candidate_asset_refs = _generate_candidate_pair(active_prompt, active_negative)
        selection = select_best_candidate(
            candidate_asset_refs=candidate_asset_refs,
            prompt=active_prompt,
            characters=asset_meta["characters"],
        )
        selection_history: List[Dict[str, Any]] = [
            summarize_selection_for_history(
                attempt=1, selection=selection, amendment_reasons=[]
            )
        ]
        attempt = 1
        # === Quality retry loop ===
        # When the selector reports should_retry (best candidate's vision score
        # plus hard-failure caps put it below MIN_PASS_SCORE), regenerate the
        # candidate pair with prompt amendments derived from the failing
        # visual_review (missing characters / forbidden traits / anatomy
        # leakage). Only accept a retry if it scored strictly higher; stop on
        # diminishing returns to avoid burning API budget for no gain.
        #
        # `preserve_seed=True` (增强画质) explicitly skips this loop:
        # the whole point of enhance is "same composition, higher quality
        # render". The retry loop would re-roll prompts and break the
        # promise that the new candidate looks like the original — even
        # with the seed pinned, prompt amendments make the model draw a
        # different scene. Setting max_retries to 0 here keeps the
        # cinematic-tier render of the original seed/prompt pair as-is.
        max_retries = 0 if preserve_seed else quality_max_retries()
        while selection.get("should_retry") and attempt <= max_retries:
            candidate_scores = selection.get("candidate_scores") or []
            failing_visual_review = (
                (candidate_scores[0].get("visual_review") if candidate_scores else {})
                or {}
            )
            amendment = derive_retry_prompt_amendment(
                base_prompt=base_prompt,
                base_negative_prompt=negative_prompt,
                visual_review=failing_visual_review,
                attempt=attempt + 1,
            )
            if not amendment.get("has_amendments"):
                # No structured failure signals to act on; retrying the same
                # prompt with the same provider is unlikely to help.
                break

            attempt += 1
            active_prompt = amendment["prompt"]
            active_negative = amendment["negative_prompt"]

            retry_candidates = _generate_candidate_pair(active_prompt, active_negative)
            retry_selection = select_best_candidate(
                candidate_asset_refs=retry_candidates,
                prompt=active_prompt,
                characters=asset_meta["characters"],
            )
            selection_history.append(
                summarize_selection_for_history(
                    attempt=attempt,
                    selection=retry_selection,
                    amendment_reasons=amendment.get("amendment_reasons") or [],
                )
            )

            if float(retry_selection.get("best_score") or 0.0) > float(
                selection.get("best_score") or 0.0
            ):
                selection = retry_selection
                candidate_asset_refs = retry_candidates
            else:
                # Retry scored no better — stop to avoid runaway API cost.
                break

        candidate_asset_refs = selection["candidate_asset_refs"]
        selected_asset_ref = selection["selected_asset_ref"]
        quality_retry_attempts = max(0, attempt - 1)
        quality_retry_exhausted = bool(selection.get("should_retry"))

        return {
            "scene_id": scene_id,
            "scene_title": asset_meta["scene_title"],
            "characters": asset_meta["characters"],
            "character_ids": asset_meta["character_ids"],
            "prompt": base_prompt,
            "negative_prompt": negative_prompt,
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
            "quality_gates": selection.get("quality_gates") or {},
            "review_required": bool(selection.get("review_required"))
            or quality_retry_exhausted,
            "quality_retry_attempts": quality_retry_attempts,
            "quality_retry_exhausted": quality_retry_exhausted,
            "selection_history": selection_history,
        }

    def run_single_scene_image_asset(
        self,
        *,
        ctx: Any,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
        preserve_seed: bool = False,
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
                    preserve_seed=preserve_seed,
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
