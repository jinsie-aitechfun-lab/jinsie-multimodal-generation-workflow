from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.character_visual_profile_llm import (
    build_llm_character_visual_profile,
    build_llm_character_visual_profiles,
)
from app.services.image_prompt_policy import (
    build_image_prompt_policy_blocks,
    clean_image_prompt_text,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _scene_position_anchor(
    scene_index: int,
    total: int,
    scene: Dict[str, Any],
    narration_text: str,
) -> str:
    """Strong scene-unique anchor placed early in the prompt.

    Diffusion models weight the beginning of the prompt most heavily. By
    inserting the current scene's position + title + a slice of the actual
    narration BEFORE the long character-identity lock blocks, the model
    is forced to encode this scene's unique story moment instead of
    settling on "a generic character portrait" shared with other scenes.
    The clean_image_prompt_text() pass strips any "主角" labels that would
    otherwise leak into the rendered image as Chinese characters.
    """
    pos = scene_index + 1
    title = str(scene.get("scene_title") or "").strip()
    moment = clean_image_prompt_text(narration_text)[:160] if narration_text else ""
    parts: List[str] = [f"scene {pos} of {total}"]
    if title:
        parts.append(f"scene title: {title}")
    if moment:
        parts.append(f"current story moment: {moment}")
    parts.append(
        "this is a unique moment of the story, not a generic character portrait"
    )
    return ", ".join(parts)


def _anti_repeat_block(scene_index: int, total: int) -> str:
    """Anti-repetition tail block — explicitly demand visual variation
    across scenes. Without this, when every scene's prompt shares the
    same long character lock, the diffusion model tends to converge on
    a single canonical pose for every scene."""
    pos = scene_index + 1
    return (
        f"this is scene {pos} of {total}; "
        "the composition, camera angle, environment, mood, and visible action "
        "must visibly differ from the other scenes of this story; "
        "do not reuse the composition, lighting, or background from any other scene"
    )


def _scene_action_fallback(
    visual_description: str,
    narration: str,
    scene_title: str,
) -> str:
    """If visual_description is empty (storyboard LLM enrichment failed),
    synthesize a scene-specific action hint from whatever IS available so
    the scene_anchor and scene_action_block don't end up empty. Without
    this, an LLM failure makes every scene's "visual focus" collapse to
    the same string and the prompts become indistinguishable."""
    visual = clean_image_prompt_text(visual_description)
    if visual:
        return visual
    story = clean_image_prompt_text(narration)
    if story:
        # Trim long narration to a focused visual hint
        return story[:200]
    title = clean_image_prompt_text(scene_title)
    if title:
        return f"the scene depicting {title}"
    return ""


def _write_image_prompts_debug(workflow_id: str, prompts: List[Dict[str, Any]]) -> None:
    """Write a per-run debug file with every scene's final prompt so the
    output can be inspected after generation. Failures here are non-fatal
    — debug logging must never break the actual image generation."""
    wf = str(workflow_id or "").strip()
    if not wf:
        return
    try:
        out_dir = PROJECT_ROOT / "assets" / "mock" / wf
        out_dir.mkdir(parents=True, exist_ok=True)
        debug_path = out_dir / "image_prompts_debug.json"
        debug_payload = {
            "workflow_id": wf,
            "scene_count": len(prompts),
            "prompts": [
                {
                    "scene_id": str(p.get("scene_id") or "").strip(),
                    "scene_title": str(p.get("scene_title") or "").strip(),
                    "required_character_names": p.get("required_character_names") or [],
                    "prompt": str(p.get("prompt") or ""),
                    "prompt_char_count": len(str(p.get("prompt") or "")),
                }
                for p in prompts
            ],
        }
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(debug_payload, f, ensure_ascii=False, indent=2)
        print(
            f"[RunnerImagePromptsSupport] wrote per-scene image prompts debug → {debug_path}"
        )
    except Exception as error:  # noqa: BLE001
        print(f"[RunnerImagePromptsSupport] image prompts debug write failed: {error}")


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
            total_shots = len(shot_items)

            for shot_index, shot in enumerate(shot_items):
                shot_id = str(shot.get("shot_id") or "").strip()
                scene_id = str(shot.get("scene_id") or "").strip()
                scene_title = str(shot.get("scene_title") or "").strip()
                visual_description = str(shot.get("visual_description") or "").strip()
                shot_type = str(shot.get("shot_type") or "medium").strip()
                transition = str(shot.get("transition") or "fade").strip()
                text = str(shot.get("text") or "").strip()

                scene_data = scene_map.get(scene_id) or {}

                # Robust scene-specific focus: when visual_description is
                # empty (LLM enrichment failed), synthesize from narration
                # or scene_title so the scene anchor isn't reduced to a
                # blank "visual focus: " that's identical across scenes.
                scene_focus = _scene_action_fallback(
                    visual_description=visual_description,
                    narration=text,
                    scene_title=scene_title,
                )
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
                compact_trait_block = runner._scene_characters.scene_character_compact_trait_block(
                    outputs, scene_data
                )

                clean_visual_description = clean_image_prompt_text(visual_description) or scene_focus

                shot_anchor = (
                    f"scene title: {scene_title}, "
                    f"camera shot: {shot_type}, "
                    f"transition feeling: {transition}, "
                    f"visual focus: {clean_visual_description}"
                )

                story_anchor = f"story context: {text}"
                # scene_focus replaces empty visual_description so the
                # policy's scene_action_block always carries scene-specific
                # content, even when the storyboard LLM enrichment failed.
                policy_blocks = build_image_prompt_policy_blocks(
                    workflow_input=ctx.input,
                    outputs=profile_outputs,
                    visual_description=visual_description or scene_focus,
                    narration=text,
                    subject_hint=character_anchor,
                )

                scene_position_anchor = _scene_position_anchor(
                    scene_index=shot_index,
                    total=total_shots,
                    scene=scene_data or {"scene_title": scene_title},
                    narration_text=text,
                )
                anti_repeat_block = _anti_repeat_block(
                    scene_index=shot_index,
                    total=total_shots,
                )
                if not character_visual_profile:
                    character_visual_profile = policy_blocks.get("profile") or {}

                # Extract the first sentence of visual_identity as a color/appearance
                # prefix to place at the very start of the prompt — diffusion models
                # weight the beginning of the prompt most heavily, so pinning the
                # character's fixed color here significantly improves consistency.
                color_prefix = self._build_color_prefix(character_visual_profile)

                is_multi_character_scene = len(required_character_names) >= 2
                # In multi-character scenes the singular color_prefix puts only the
                # PRIMARY character at position 0 (e.g. "white rabbit, white fur").
                # The diffusion model then renders BOTH characters as the same
                # species — "two mirrored rabbits" instead of "rabbit + squirrel".
                # Override position 0 with a builder that names every species and
                # adds explicit "not two <species>" negatives.
                if is_multi_character_scene:
                    multi_prefix = self._build_multi_character_color_prefix(
                        character_visual_profiles
                    )
                    if multi_prefix:
                        color_prefix = multi_prefix
                # `scene_position_anchor` is placed right after color_prefix
                # so the early-prompt weight (most important for diffusion)
                # encodes THIS scene's identity before the shared
                # character-lock blocks. `anti_repeat_block` is appended at
                # the very end so the negative-style instruction caps the
                # sequence with explicit "do not duplicate previous scene".
                prompt_parts = [
                    color_prefix,
                    scene_position_anchor,
                    global_style_anchor,
                    shot_anchor,
                    character_anchor,
                    policy_blocks.get("visual_profile_block"),
                    policy_blocks.get("character_visual_profiles_block"),
                    character_block,
                    scene_required_presence_block,
                    policy_blocks.get("character_separation_block"),
                    policy_blocks.get("scene_action_block"),
                    story_anchor,
                    policy_blocks.get("subject_negative_block"),
                    negative_block,
                    anti_repeat_block,
                ]
                if is_multi_character_scene:
                    prompt_parts = [
                        color_prefix,
                        scene_position_anchor,
                        global_style_anchor,
                        compact_trait_block,
                        shot_anchor,
                        scene_required_presence_block,
                        character_block,
                        policy_blocks.get("character_visual_profiles_block"),
                        policy_blocks.get("character_separation_block"),
                        policy_blocks.get("scene_action_block"),
                        story_anchor,
                        negative_block,
                        anti_repeat_block,
                    ]

                prompt = ", ".join(
                    part for part in prompt_parts if part
                )

                prompts.append(
                    {
                        "shot_id": shot_id,
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

            _write_image_prompts_debug(getattr(ctx, "workflow_id", ""), prompts)
            return {
                "provider": "image_prompt_builder",
                "character_visual_profile": character_visual_profile,
                "character_visual_profiles": character_visual_profiles,
                "character_anchor": character_anchor_metadata,
                "prompts": prompts,
            }

        total_scenes = len(scenes)
        for scene_index, scene in enumerate(scenes):
            scene_id = str(scene.get("scene_id") or "").strip()
            narration = str(scene.get("narration", "")).strip()
            visual_description = str(scene.get("visual_description", "")).strip()
            shot_type = str(scene.get("shot_type", "medium")).strip()
            transition = str(scene.get("transition", "fade")).strip()
            scene_title = str(scene.get("scene_title", "")).strip()

            # Robust scene focus fallback so the per-scene visual content
            # is never blank even when storyboard LLM enrichment fails.
            scene_focus = _scene_action_fallback(
                visual_description=visual_description,
                narration=narration,
                scene_title=scene_title,
            )
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
            compact_trait_block = runner._scene_characters.scene_character_compact_trait_block(
                outputs, scene
            )

            clean_visual_description = clean_image_prompt_text(visual_description) or scene_focus

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
                visual_description=visual_description or scene_focus,
                narration=narration,
                subject_hint=character_anchor,
            )

            scene_position_anchor = _scene_position_anchor(
                scene_index=scene_index,
                total=total_scenes,
                scene=scene,
                narration_text=narration,
            )
            anti_repeat_block = _anti_repeat_block(
                scene_index=scene_index,
                total=total_scenes,
            )
            if not character_visual_profile:
                character_visual_profile = policy_blocks.get("profile") or {}

            color_prefix = self._build_color_prefix(character_visual_profile)

            is_multi_character_scene = len(required_character_names) >= 2
            # Override position 0 with the multi-character species anchor when
            # there are 2+ required characters — see commentary in the shot
            # branch above. Without this, both characters render as the
            # primary species (mirrored rabbits / mirrored squirrels).
            if is_multi_character_scene:
                multi_prefix = self._build_multi_character_color_prefix(
                    character_visual_profiles
                )
                if multi_prefix:
                    color_prefix = multi_prefix
            # scene_position_anchor goes early so this scene's identity
            # gets the most attention from the diffusion model; the
            # anti_repeat_block goes last so the negative-style demand
            # to differ from other scenes is the final instruction.
            prompt_parts = [
                color_prefix,
                scene_position_anchor,
                global_style_anchor,
                scene_anchor,
                character_anchor,
                policy_blocks.get("visual_profile_block"),
                policy_blocks.get("character_visual_profiles_block"),
                character_block,
                scene_required_presence_block,
                policy_blocks.get("character_separation_block"),
                policy_blocks.get("scene_action_block"),
                story_anchor,
                policy_blocks.get("subject_negative_block"),
                negative_block,
                anti_repeat_block,
            ]
            if is_multi_character_scene:
                prompt_parts = [
                    color_prefix,
                    scene_position_anchor,
                    global_style_anchor,
                    compact_trait_block,
                    scene_anchor,
                    scene_required_presence_block,
                    character_block,
                    policy_blocks.get("character_visual_profiles_block"),
                    policy_blocks.get("character_separation_block"),
                    policy_blocks.get("scene_action_block"),
                    story_anchor,
                    negative_block,
                    anti_repeat_block,
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

        _write_image_prompts_debug(getattr(ctx, "workflow_id", ""), prompts)
        return {
            "provider": "image_prompt_builder",
            "character_visual_profile": character_visual_profile,
            "character_visual_profiles": character_visual_profiles,
            "character_anchor": character_anchor_metadata,
            "prompts": prompts,
        }

    def _build_multi_character_color_prefix(
        self,
        character_visual_profiles: Dict[str, Any],
    ) -> str:
        """Position-0 prefix for multi-character scenes.

        When a scene has 2+ required characters, the singular
        `_build_color_prefix(profile)` (which only sees the PRIMARY
        character) puts "white rabbit, white fur" at the start of the
        prompt — diffusion weights this most heavily and the model
        then renders BOTH characters as rabbits (or even mirrored
        copies of one rabbit). This builder pulls every character's
        species + the first color trait so the very first tokens of
        the prompt are "white long-eared rabbit and brown bushy-tailed
        squirrel, two different animal species". The explicit
        "not two <species>" negatives are critical — diffusion models
        respond strongly to that pattern when it appears early.
        """
        profiles = (character_visual_profiles or {}).get("profiles") or []
        if not isinstance(profiles, list) or len(profiles) < 2:
            return ""

        COLOR_WORDS = {
            "red", "blue", "green", "yellow", "orange", "purple", "pink",
            "white", "black", "gray", "grey", "brown", "gold", "silver",
            "cream", "teal", "cyan", "magenta", "violet", "indigo",
            "红", "蓝", "绿", "黄", "橙", "紫", "粉", "白", "黑", "灰", "棕", "金",
        }

        labels: List[str] = []
        species_set: List[str] = []

        for profile in profiles:
            if not isinstance(profile, dict):
                continue

            species = str(profile.get("species") or "").strip()
            display = str(profile.get("display_name") or "").strip()
            subject = str(profile.get("subject") or "").strip()
            identity = str(profile.get("visual_identity") or "").strip()
            must_keep = profile.get("must_keep") or []
            if not isinstance(must_keep, list):
                must_keep = []

            # Pick the first must_keep trait that carries a color word
            # so the label reads as "{color/trait} {species}" — e.g.
            # "white long-eared rabbit" or "brown bushy-tailed squirrel".
            color_trait = ""
            for trait in must_keep:
                t = str(trait or "").strip()
                if not t:
                    continue
                if any(c in t.lower() for c in COLOR_WORDS):
                    color_trait = t
                    break
            if not color_trait and identity:
                color_trait = identity.split(".")[0].strip()

            anchor_species = species or display or subject
            if not anchor_species:
                continue
            if anchor_species not in species_set:
                species_set.append(anchor_species)

            label = (
                f"{color_trait} {anchor_species}".strip()
                if color_trait
                else anchor_species
            )
            if label and label not in labels:
                labels.append(label)

        if len(labels) < 2:
            return ""

        parts: List[str] = []
        # "X and Y" — both characters named at the very start.
        parts.append(" and ".join(labels))
        parts.append(f"two different animal species in one image: {', '.join(species_set)}")
        # Explicit negatives by species — strongest known anti-mirror
        # signal for diffusion models when placed early in the prompt.
        for s in species_set:
            parts.append(f"not two {s}")
        parts.append("do not draw mirrored characters")
        parts.append("do not draw both characters as the same species")
        return ", ".join(parts)

    def _build_color_prefix(self, profile: Dict[str, Any]) -> str:
        """Return a tight color+identity anchor prepended to every scene prompt.

        Diffusion models weight the beginning of the prompt most heavily.
        We extract the subject name and any must_keep items that contain a
        color word, then put "subject, color_trait1, color_trait2" first.
        This is more reliable than truncating visual_identity which often
        buries the color word past 120 characters.
        """
        if not profile:
            return ""

        COLOR_WORDS = {
            "red", "blue", "green", "yellow", "orange", "purple", "pink",
            "white", "black", "gray", "grey", "brown", "gold", "silver",
            "cream", "teal", "cyan", "magenta", "violet", "indigo",
            "红", "蓝", "绿", "黄", "橙", "紫", "粉", "白", "黑", "灰", "棕", "金",
        }

        subject = str(profile.get("subject") or "").strip()
        must_keep = profile.get("must_keep") or []
        if not isinstance(must_keep, list):
            must_keep = []

        # Pick must_keep entries that mention a color word (max 3)
        color_traits: List[str] = []
        for trait in must_keep:
            t = str(trait).strip()
            if not t:
                continue
            lower = t.lower()
            if any(c in lower for c in COLOR_WORDS) and t not in color_traits:
                color_traits.append(t)
            if len(color_traits) >= 3:
                break

        # Fallback: use first full sentence of visual_identity (no truncation)
        if not color_traits:
            identity = str(profile.get("visual_identity") or "").strip()
            if identity:
                first_sentence = identity.split(".")[0].strip()
                if len(first_sentence) > 10:
                    return first_sentence

        parts = [p for p in [subject] + color_traits if p]
        return ", ".join(parts) if parts else ""
