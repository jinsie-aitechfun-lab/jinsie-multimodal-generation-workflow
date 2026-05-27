from __future__ import annotations

from typing import Any, Dict, List

from app.services.character_visual_profile_llm import (
    build_llm_character_visual_profile,
    build_llm_character_visual_profiles,
)
from app.services.image_prompt_policy import (
    build_image_prompt_policy_blocks,
    clean_image_prompt_text,
)


class RunnerImagePromptsSupport:
    """Image prompt assembly extracted from WorkflowRunner.

    Extracted as Step 11 of the runner refactor. This module owns the
    image-prompt output assembly and character anchor metadata while delegating
    shared character and scene helpers back to WorkflowRunner.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def run_image_prompts(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        runner = self._runner
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        image_size = __import__("os").getenv(
            "SILICONFLOW_IMAGE_SIZE", "1280x720"
        ).strip()
        framing = "vertical 9:16 framing" if image_size.startswith("720") else "horizontal 16:9 framing"
        global_style_anchor = (
            f"{ctx.input.visual_style} illustration, "
            f"{ctx.input.tone} mood, "
            "children's storybook art, "
            "soft pastel palette, "
            "warm gentle lighting, "
            "clean composition, "
            "consistent character design, "
            f"{framing}"
        )

        character_anchor = runner._character_consistency_anchor(ctx, outputs)

        prompts: List[Dict[str, Any]] = []
        character_visual_profile: Dict[str, Any] = build_llm_character_visual_profile(
            runner,
            ctx,
            outputs,
            subject_hint=character_anchor,
        )
        character_visual_profiles: Dict[str, Any] = build_llm_character_visual_profiles(
            runner,
            ctx,
            outputs,
        )

        enriched_character_manifest = runner._character_manifest_support.apply_visual_profiles_to_character_manifest(
            outputs.get("character_manifest") or {},
            character_visual_profiles,
        )
        if enriched_character_manifest:
            outputs["character_manifest"] = enriched_character_manifest

        character_anchor_metadata: Dict[str, Any] = {
            "enabled": True,
            "mode": "text_profile_anchor",
            "anchor_type": "character_reference_anchor",
            "subject": character_visual_profile.get("subject"),
            "profile_source": character_visual_profile.get("profile_source"),
            "profile_generation_source": character_visual_profile.get(
                "profile_generation_source"
            ),
            "visual_identity": character_visual_profile.get("visual_identity"),
            "reference_images": [],
            "reference_image": None,
            "provider_reference_support": {
                "requested": True,
                "provider_supports_reference_image": False,
                "mode": "metadata_only",
                "reason": (
                    "current api_image_generator text-to-image adapter does not "
                    "send reference images yet"
                ),
            },
        }

        profile_outputs: Dict[str, Any] = {
            **outputs,
            "character_visual_profile": character_visual_profile,
            "character_visual_profiles": character_visual_profiles,
            "character_anchor": character_anchor_metadata,
        }

        if shot_items:
            scene_map: Dict[str, Dict[str, Any]] = {
                str(scene.get("scene_id") or "").strip(): scene
                for scene in scenes
                if isinstance(scene, dict)
            }

            for shot in shot_items:
                shot_id = str(shot.get("shot_id") or "").strip()
                scene_id = str(shot.get("scene_id") or "").strip()
                scene_title = str(shot.get("scene_title") or "").strip()
                visual_description = str(shot.get("visual_description") or "").strip()
                shot_type = str(shot.get("shot_type") or "medium").strip()
                transition = str(shot.get("transition") or "fade").strip()
                text = str(shot.get("text") or "").strip()

                scene_data = scene_map.get(scene_id) or {}
                enriched_scene_characters = (
                    runner._scene_characters.enriched_scene_characters_from_manifest(
                        outputs,
                        scene_data,
                    )
                )
                required_character_ids = (
                    runner._scene_characters.character_ids_from_bindings(
                        enriched_scene_characters
                    )
                )
                required_character_names = (
                    runner._scene_characters.character_names_from_bindings(
                        enriched_scene_characters
                    )
                )
                character_block = runner._scene_characters.scene_character_prompt_block(
                    outputs, scene_data
                )
                scene_required_presence_block = (
                    runner._scene_characters.scene_character_required_presence_block(
                        outputs, scene_data
                    )
                )
                negative_block = runner._scene_characters.scene_character_negative_block(
                    outputs, scene_data
                )

                clean_visual_description = clean_image_prompt_text(visual_description)

                shot_anchor = (
                    f"scene title: {scene_title}, "
                    f"camera shot: {shot_type}, "
                    f"transition feeling: {transition}, "
                    f"visual focus: {clean_visual_description}"
                )

                story_anchor = f"story context: {text}"
                policy_blocks = build_image_prompt_policy_blocks(
                    workflow_input=ctx.input,
                    outputs=profile_outputs,
                    visual_description=visual_description,
                    narration=text,
                    subject_hint=character_anchor,
                )
                if not character_visual_profile:
                    character_visual_profile = policy_blocks.get("profile") or {}

                is_multi_character_scene = len(required_character_names) >= 2
                prompt_parts = [
                    global_style_anchor,
                    character_anchor,
                    policy_blocks.get("visual_profile_block"),
                    policy_blocks.get("character_visual_profiles_block"),
                    character_block,
                    scene_required_presence_block,
                    policy_blocks.get("character_separation_block"),
                    shot_anchor,
                    policy_blocks.get("scene_action_block"),
                    story_anchor,
                    policy_blocks.get("subject_negative_block"),
                    negative_block,
                ]
                if is_multi_character_scene:
                    prompt_parts = [
                        global_style_anchor,
                        scene_required_presence_block,
                        character_block,
                        policy_blocks.get("character_visual_profiles_block"),
                        policy_blocks.get("character_separation_block"),
                        shot_anchor,
                        policy_blocks.get("scene_action_block"),
                        story_anchor,
                        negative_block,
                    ]

                prompt = ", ".join(
                    part for part in prompt_parts if part
                )

                prompts.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "characters": scene_data.get("characters") or [],
                        "required_character_ids": required_character_ids,
                        "required_character_names": required_character_names,
                        "prompt": prompt,
                        "character_anchor": character_anchor_metadata,
                        "reference_images": character_anchor_metadata.get(
                            "reference_images"
                        )
                        or [],
                    }
                )

            return {
                "provider": "image_prompt_builder",
                "character_visual_profile": character_visual_profile,
                "character_visual_profiles": character_visual_profiles,
                "character_anchor": character_anchor_metadata,
                "prompts": prompts,
            }

        for scene in scenes:
            scene_id = str(scene.get("scene_id") or "").strip()
            narration = str(scene.get("narration", "")).strip()
            visual_description = str(scene.get("visual_description", "")).strip()
            shot_type = str(scene.get("shot_type", "medium")).strip()
            transition = str(scene.get("transition", "fade")).strip()
            scene_title = str(scene.get("scene_title", "")).strip()
            enriched_scene_characters = (
                runner._scene_characters.enriched_scene_characters_from_manifest(
                    outputs,
                    scene,
                )
            )
            required_character_ids = runner._scene_characters.character_ids_from_bindings(
                enriched_scene_characters
            )
            required_character_names = (
                runner._scene_characters.character_names_from_bindings(
                    enriched_scene_characters
                )
            )

            character_block = runner._scene_characters.scene_character_prompt_block(
                outputs, scene
            )
            scene_required_presence_block = (
                runner._scene_characters.scene_character_required_presence_block(
                    outputs, scene
                )
            )
            negative_block = runner._scene_characters.scene_character_negative_block(
                outputs, scene
            )

            clean_visual_description = clean_image_prompt_text(visual_description)

            scene_anchor = (
                f"scene title: {scene_title}, "
                f"camera shot: {shot_type}, "
                f"transition feeling: {transition}, "
                f"visual focus: {clean_visual_description}"
            )

            story_anchor = f"story context: {narration}"
            policy_blocks = build_image_prompt_policy_blocks(
                workflow_input=ctx.input,
                outputs=profile_outputs,
                visual_description=visual_description,
                narration=narration,
                subject_hint=character_anchor,
            )
            if not character_visual_profile:
                character_visual_profile = policy_blocks.get("profile") or {}

            is_multi_character_scene = len(required_character_names) >= 2
            prompt_parts = [
                global_style_anchor,
                character_anchor,
                policy_blocks.get("visual_profile_block"),
                policy_blocks.get("character_visual_profiles_block"),
                character_block,
                scene_required_presence_block,
                policy_blocks.get("character_separation_block"),
                scene_anchor,
                policy_blocks.get("scene_action_block"),
                story_anchor,
                policy_blocks.get("subject_negative_block"),
                negative_block,
            ]
            if is_multi_character_scene:
                prompt_parts = [
                    global_style_anchor,
                    scene_required_presence_block,
                    character_block,
                    policy_blocks.get("character_visual_profiles_block"),
                    policy_blocks.get("character_separation_block"),
                    scene_anchor,
                    policy_blocks.get("scene_action_block"),
                    story_anchor,
                    negative_block,
                ]

            prompt = ", ".join(
                part for part in prompt_parts if part
            )

            prompts.append(
                {
                    "scene_id": scene_id,
                    "scene_title": scene_title,
                    "characters": enriched_scene_characters,
                    "required_character_ids": required_character_ids,
                    "required_character_names": required_character_names,
                    "prompt": prompt,
                    "character_anchor": character_anchor_metadata,
                    "reference_images": character_anchor_metadata.get(
                        "reference_images"
                    )
                    or [],
                }
            )

        return {
            "provider": "image_prompt_builder",
            "character_visual_profile": character_visual_profile,
            "character_visual_profiles": character_visual_profiles,
            "character_anchor": character_anchor_metadata,
            "prompts": prompts,
        }
