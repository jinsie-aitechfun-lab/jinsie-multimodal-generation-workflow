from __future__ import annotations

from typing import Any, Dict, List

from app.services.runner_errors import UnknownVideoProviderError


class RunnerVideoPromptsSupport:
    """Per-provider video prompt builders (mock / kling / jimeng) and
    their dedicated scene/metadata helpers.

    Extracted from WorkflowRunner as Step 4 of the runner refactor.
    All methods are pure data assembly on scene dicts and outputs dicts.
    No async, no LLM, no IO.

    Dispatch shape mirrors RunnerRenderPlanSupport (Step 3):
    build_video_provider_prompts routes by provider, dedicated builders
    return a provider-specific prompts payload, and any unknown provider
    triggers UnknownVideoProviderError.

    Three small helpers are owned by this module because nothing outside
    the video-prompts family uses them:

    - character_prompt_phrase    : pure ctx-derived label
    - video_prompt_scene_metadata: assembles scene-level metadata
                                   (characters / image asset refs /
                                   selection status) consumed by
                                   attach_video_prompt_contract
    - attach_video_prompt_contract: enriches a per-scene prompt item with
                                    the contract fields the API exposes
                                    (characters / character_ids /
                                    selected_asset_ref / image_asset_ref
                                    / selection_source / selection_mode
                                    / review_status)
    - build_video_prompt_base    : normalizes the scene-level inputs
                                   (titles / descriptions / shot type /
                                   transition) into a stable dict used
                                   by every provider builder

    External dependencies that stay on WorkflowRunner and are reached
    via self._runner:

    - _normalized_video_provider          (also used by image code)
    - _main_character_display_label       (shared utility)
    - _image_review.selection_item_by_scene_id (Step 2 module)

    Behavior must remain byte-for-byte identical to the original
    methods in runner.py. Callers were updated to use
    self._video_prompts.build_video_provider_prompts(...) at the two
    runner.py call sites (manual-image-selection refresh + the
    video_prompts step handler).
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def character_prompt_phrase(self, ctx: Any) -> str:
        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_character:
            return main_character
        return f"{ctx.input.character_style} protagonist"

    def video_prompt_scene_metadata(
        self,
        scene: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        characters = scene.get("characters") or []
        if not isinstance(characters, list):
            characters = []

        character_ids: List[str] = []
        seen = set()
        for item in characters:
            if not isinstance(item, dict):
                continue
            character_id = str(item.get("character_id") or "").strip()
            if character_id and character_id not in seen:
                character_ids.append(character_id)
                seen.add(character_id)

        scene_id = str(scene.get("scene_id") or "").strip()
        selection_item = (
            self._runner._image_review.selection_item_by_scene_id(outputs).get(scene_id)
            or {}
        )
        selected_asset_ref = selection_item.get("selected_asset_ref") or {}

        return {
            "characters": characters,
            "character_ids": character_ids,
            "selected_asset_ref": selected_asset_ref,
            "image_asset_ref": selected_asset_ref,
            "selection_source": str(
                selection_item.get("selection_source") or "unknown"
            ).strip(),
            "selection_mode": str(
                selection_item.get("selection_mode") or "unknown"
            ).strip(),
            "review_status": str(
                selection_item.get("review_status") or "unreviewed"
            ).strip(),
        }

    def attach_video_prompt_contract(
        self,
        prompt_item: Dict[str, Any],
        scene: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        meta = self.video_prompt_scene_metadata(scene, outputs)
        enriched = dict(prompt_item)
        enriched["characters"] = meta["characters"]
        enriched["character_ids"] = meta["character_ids"]
        enriched["selected_asset_ref"] = meta["selected_asset_ref"]
        enriched["image_asset_ref"] = meta["image_asset_ref"]
        enriched["selection_source"] = meta["selection_source"]
        enriched["selection_mode"] = meta["selection_mode"]
        enriched["review_status"] = meta["review_status"]
        return enriched

    def build_video_prompt_base(
        self,
        ctx: Any,
        scene: Dict[str, Any],
    ) -> Dict[str, Any]:
        scene_id = str(scene.get("scene_id") or "").strip()
        scene_title = str(scene.get("scene_title") or "").strip()
        visual_description = str(scene.get("visual_description") or "").strip()
        narration = str(scene.get("narration") or "").strip()
        duration_sec = int(scene.get("duration_sec") or 0)
        shot_type = str(scene.get("shot_type") or "medium").strip()
        transition = str(scene.get("transition") or "fade").strip()

        if not scene_title:
            scene_title = scene_id or "scene"

        if not visual_description:
            main_character = self._runner._main_character_display_label(ctx)
            visual_description = (
                f"{ctx.input.visual_style} 风格画面，主角 {main_character} 出现在当前场景中。"
            )

        if not narration:
            narration = scene_title

        return {
            "scene_id": scene_id,
            "scene_title": scene_title,
            "visual_description": visual_description,
            "narration": narration,
            "duration_sec": duration_sec,
            "shot_type": shot_type,
            "transition": transition,
        }

    def build_video_provider_prompts(
        self,
        ctx: Any,
        scenes: List[Dict[str, Any]],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        provider = self._runner._normalized_video_provider(ctx.input.video_provider)

        if provider == "mock":
            return self.build_mock_video_prompts(ctx, scenes, outputs)
        if provider == "kling":
            return self.build_kling_video_prompts(ctx, scenes, outputs)
        if provider == "jimeng":
            return self.build_jimeng_video_prompts(ctx, scenes, outputs)

        raise UnknownVideoProviderError(f"Unknown video provider: {provider}")

    def build_mock_video_prompts(
        self,
        ctx: Any,
        scenes: List[Dict[str, Any]],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompts: List[Dict[str, Any]] = []
        character_phrase = self.character_prompt_phrase(ctx)

        for scene in scenes:
            base = self.build_video_prompt_base(ctx, scene)
            prompt = (
                f"Create a short animated video shot in {ctx.input.visual_style} style, "
                f"{ctx.input.tone} atmosphere, with {character_phrase}. "
                f"Scene description: {base['visual_description']}. "
                f"Narration context: {base['narration']}"
            )

            item = {
                "scene_id": base["scene_id"],
                "scene_title": base["scene_title"],
                "provider": "mock",
                "prompt": prompt,
                "duration_sec": base["duration_sec"],
                "shot_type": base["shot_type"],
                "transition": base["transition"],
            }
            prompts.append(self.attach_video_prompt_contract(item, scene, outputs))

        return {
            "provider": "mock",
            "mode": "placeholder",
            "integration_status": "mock_only",
            "prompts": prompts,
        }

    def build_kling_video_prompts(
        self,
        ctx: Any,
        scenes: List[Dict[str, Any]],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompts: List[Dict[str, Any]] = []
        character_phrase = self.character_prompt_phrase(ctx)

        for scene in scenes:
            base = self.build_video_prompt_base(ctx, scene)
            item = {
                "scene_id": base["scene_id"],
                "scene_title": base["scene_title"],
                "provider": "kling",
                "prompt": (
                    f"[KLING] style={ctx.input.visual_style}; tone={ctx.input.tone}; "
                    f"character={character_phrase}; shot={base['shot_type']}; "
                    f"scene={base['visual_description']}; narration={base['narration']}"
                ),
                "duration_sec": base["duration_sec"],
                "shot_type": base["shot_type"],
                "transition": base["transition"],
                "api_ready": False,
            }
            prompts.append(self.attach_video_prompt_contract(item, scene, outputs))

        return {
            "provider": "kling",
            "mode": "adapter_placeholder",
            "integration_status": "pending_api_integration",
            "prompts": prompts,
        }

    def build_jimeng_video_prompts(
        self,
        ctx: Any,
        scenes: List[Dict[str, Any]],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompts: List[Dict[str, Any]] = []
        character_phrase = self.character_prompt_phrase(ctx)

        for scene in scenes:
            base = self.build_video_prompt_base(ctx, scene)
            item = {
                "scene_id": base["scene_id"],
                "scene_title": base["scene_title"],
                "provider": "jimeng",
                "prompt": (
                    f"[JIMENG] visual={ctx.input.visual_style}; atmosphere={ctx.input.tone}; "
                    f"role={character_phrase}; transition={base['transition']}; "
                    f"scene={base['visual_description']}; narration={base['narration']}"
                ),
                "duration_sec": base["duration_sec"],
                "shot_type": base["shot_type"],
                "transition": base["transition"],
                "api_ready": False,
            }
            prompts.append(self.attach_video_prompt_contract(item, scene, outputs))

        return {
            "provider": "jimeng",
            "mode": "adapter_placeholder",
            "integration_status": "pending_api_integration",
            "prompts": prompts,
        }
