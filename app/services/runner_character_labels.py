from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.story_subject_extractor import (
    extract_story_subjects,
    story_main_subject,
)
from app.services.topic_character_infer import infer_primary_character_manifest


class RunnerCharacterLabelsSupport:
    """Character display labels and visual consistency anchors.

    Extracted as Step 13 of the runner refactor. These helpers keep topic
    cleanup, character fallback labels, and prompt anchor text in one place.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def clean_story_topic(self, topic: str) -> str:
        candidate = " ".join(str(topic or "").split()).strip()
        if not candidate:
            return ""

        for prefix in (
            "请帮我写一个关于",
            "帮我写一个关于",
            "写一个关于",
            "讲一个关于",
            "生成一个关于",
            "关于",
        ):
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix) :].strip()
                break

        for suffix in (
            "的故事",
            "故事",
            "绘本",
            "视频",
            "动画",
            "短片",
        ):
            if candidate.endswith(suffix):
                candidate = candidate[: -len(suffix)].strip()
                break

        return candidate.strip(" \\t\\n\\r，。！？、,.!?：:；;“”\\\"'《》")

    def topic_primary_character_display_label(self, ctx: Any) -> str:
        topic = self.clean_story_topic(ctx.input.topic)
        if not topic:
            return ""

        policy_subject = story_main_subject(topic)
        if policy_subject and policy_subject != "主角":
            return policy_subject

        try:
            inferred = infer_primary_character_manifest(topic)
        except Exception:
            inferred = None

        if isinstance(inferred, dict):
            display = str(inferred.get("display_name") or "").strip()
            species = str(inferred.get("species") or "").strip()
            if display and display != topic:
                return display
            if species and species != topic:
                return species

        return ""

    def main_character_display_label(
        self,
        ctx: Any,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        runner = self._runner

        if outputs:
            manifest_item = (
                runner._character_manifest_support.manifest_character_by_role(
                    outputs, "primary"
                )
            )
            if manifest_item is not None:
                display_value = str(manifest_item.get("display_name") or "").strip()
                if display_value:
                    return display_value

        display_value = str(
            getattr(ctx.input, "main_character_display", "") or ""
        ).strip()
        if display_value:
            return display_value

        main_value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_value:
            return main_value

        topic_character = self.topic_primary_character_display_label(ctx)
        if topic_character:
            return topic_character

        return runner._character_style_label(ctx.input.character_style)

    def secondary_character_display_label(
        self,
        ctx: Any,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        runner = self._runner

        if outputs:
            manifest_item = (
                runner._character_manifest_support.manifest_character_by_role(
                    outputs, "secondary"
                )
            )
            if manifest_item is not None:
                display_value = str(manifest_item.get("display_name") or "").strip()
                if display_value:
                    return display_value

        display_value = str(
            getattr(ctx.input, "secondary_character_display", "") or ""
        ).strip()
        if display_value:
            return display_value

        secondary_value = str(
            getattr(ctx.input, "secondary_character", "") or ""
        ).strip()
        if secondary_value:
            return secondary_value

        extracted_subjects = extract_story_subjects(ctx.input.topic)
        if extracted_subjects.supporting_subjects:
            return extracted_subjects.supporting_subjects[0]

        return ""

    def has_secondary_character(
        self,
        ctx: Any,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return bool(self.secondary_character_display_label(ctx, outputs))

    def main_character_label(self, ctx: Any) -> str:
        value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if value:
            return value
        return self._runner._character_style_label(ctx.input.character_style)

    def main_character_subject(self, ctx: Any) -> str:
        value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if value:
            return value
        return f"{ctx.input.character_style} protagonist"

    def visual_subject_constraints(self, subject: str) -> str:
        value = str(subject or "").strip()
        if not value:
            return ""

        if "蝌蚪" in value:
            return (
                "tadpole, round head, long tail, swimming in water, "
                "no frog legs, no adult frog body, not a frog"
            )

        return ""

    def character_consistency_anchor(
        self,
        ctx: Any,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        explicit_anchor = str(
            getattr(ctx.input, "character_consistency_anchor", "") or ""
        ).strip()
        if explicit_anchor:
            return explicit_anchor

        primary = None
        if outputs:
            primary = self._runner._character_manifest_support.manifest_character_by_role(
                outputs, "primary"
            )

        if isinstance(primary, dict):
            display = str(primary.get("display_name") or "").strip()
            species = str(primary.get("species") or "").strip()
            traits = str(primary.get("visual_traits") or "").strip()
            forbid = str(primary.get("forbidden_traits") or "").strip()

            parts = []
            if display and species:
                parts.append(f"{display} ({species})")
            elif species:
                parts.append(species)
            elif display:
                parts.append(display)

            if traits:
                parts.append(traits)

            if forbid:
                parts.append(f"avoid: {forbid}")

            parts.extend(
                [
                    "same character across all scenes",
                    "consistent facial features",
                    "consistent body shape",
                    "consistent outfit and visual identity",
                    "cute expressive face",
                    "storybook details",
                ]
            )
            return ", ".join([p for p in parts if p])

        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()
        generic_subjects = {
            "",
            "animal protagonist",
            "protagonist",
            "character",
        }
        if main_character and main_character.lower() not in generic_subjects:
            visual_constraints = self.visual_subject_constraints(main_character)
            parts = [
                f"main subject: {main_character}",
                visual_constraints,
                "same main subject across all scenes",
                "consistent visual identity",
                "consistent body shape",
                "cute expressive face",
                "storybook details",
            ]
            return ", ".join([part for part in parts if part])

        derived_subject = self.main_character_display_label(ctx, outputs)
        if derived_subject and derived_subject.lower() not in generic_subjects:
            visual_constraints = self.visual_subject_constraints(derived_subject)
            parts = [
                f"main subject: {derived_subject}",
                visual_constraints,
                "same main subject across all scenes",
                "consistent visual identity",
                "consistent body shape",
                "cute expressive face",
                "storybook details",
            ]
            return ", ".join([part for part in parts if part])

        return (
            f"main subject: {ctx.input.character_style} protagonist, "
            "same main subject across all scenes, "
            "consistent visual identity, "
            "consistent body shape, "
            "cute expressive face, "
            "storybook details"
        )
