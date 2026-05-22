from __future__ import annotations

from typing import Any, Dict


class RunnerVoiceSupport:
    """Voice mode, speaker detection, and dialogue line helpers.

    Extracted as Step 16 of the runner refactor. These helpers are pure
    payload-shaping utilities used by RunnerAudioRenderSupport.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def normalized_voice_mode(self, voice_mode: str) -> str:
        value = voice_mode.strip().lower()
        if value in {"single", "multi", "character"}:
            return value
        return "single"

    def speaker_profiles(self, ctx: Any) -> Dict[str, str]:
        profiles = dict(ctx.input.speaker_profiles or {})
        return {
            "narrator": profiles.get("narrator", ctx.input.voice_style),
            "mother": profiles.get("mother", "warm_female"),
            "child": profiles.get("child", "gentle_child"),
        }

    def character_speaker_profiles(self, ctx: Any) -> Dict[str, str]:
        profiles = dict(getattr(ctx.input, "character_speaker_profiles", {}) or {})
        return {
            "narrator": profiles.get("narrator", ctx.input.voice_style),
            "main_character": profiles.get("main_character", "gentle_child"),
            "secondary_character": profiles.get("secondary_character", "warm_male"),
        }

    def character_speaker_name(self, ctx: Any) -> str:
        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_character:
            normalized = main_character.lower().replace(" ", "_")
            return normalized
        return "main_character"

    def secondary_character_speaker_name(self, ctx: Any) -> str:
        secondary_character = str(
            getattr(ctx.input, "secondary_character", "") or ""
        ).strip()
        if secondary_character:
            normalized = secondary_character.lower().replace(" ", "_")
            return normalized
        return "secondary_character"

    def detect_character_speaker(self, ctx: Any, text: str) -> str:
        normalized = str(text or "").strip()
        if not normalized:
            return "narrator"

        main_display = str(
            getattr(ctx.input, "main_character_display", "") or ""
        ).strip()
        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()

        secondary_display = str(
            getattr(ctx.input, "secondary_character_display", "") or ""
        ).strip()
        secondary_character = str(
            getattr(ctx.input, "secondary_character", "") or ""
        ).strip()

        narrator_markers = [
            "在一个",
            "这是一个",
            "整体上",
            "这个故事",
            "画面里",
            "适合小朋友观看",
            "适合用",
            "展开了一段",
        ]
        if any(marker in normalized for marker in narrator_markers):
            return "narrator"

        if "故事的主角" in normalized:
            return "main_character"

        has_main_display = bool(main_display and main_display in normalized)
        has_main_character = bool(
            main_character and main_character.lower() in normalized.lower()
        )
        has_secondary_display = bool(
            secondary_display and secondary_display in normalized
        )
        has_secondary_character = bool(
            secondary_character and secondary_character.lower() in normalized.lower()
        )

        has_main = has_main_display or has_main_character
        has_secondary = has_secondary_display or has_secondary_character

        if has_main and has_secondary:
            return "narrator"

        if has_secondary:
            return "secondary_character"

        if has_main:
            return "main_character"

        trigger_words = [
            "说",
            "问",
            "回答",
            "喊",
            "叫",
            "小声说",
            "大声说",
            "轻声说",
            "嘀咕",
        ]
        if any(word in normalized for word in trigger_words):
            return "main_character"

        return "narrator"

    def resolve_character_speaker(self, ctx: Any, text: str) -> Dict[str, str]:
        character_profiles = self.character_speaker_profiles(ctx)
        main_character_speaker = self.character_speaker_name(ctx)
        secondary_character_speaker = self.secondary_character_speaker_name(ctx)

        detected_role = self.detect_character_speaker(ctx, text)

        if detected_role == "main_character":
            return {
                "speaker": main_character_speaker,
                "voice_style": character_profiles["main_character"],
            }

        if detected_role == "secondary_character":
            return {
                "speaker": secondary_character_speaker,
                "voice_style": character_profiles["secondary_character"],
            }

        return {
            "speaker": "narrator",
            "voice_style": character_profiles["narrator"],
        }

    def build_dialogue_line(
        self,
        *,
        line_id: str,
        text: str,
        scene_id: Any = None,
        shot_id: Any = None,
        speaker: str,
        voice_style: str,
    ) -> Dict[str, Any]:
        line: Dict[str, Any] = {
            "line_id": line_id,
            "speaker": speaker,
            "voice_style": voice_style,
            "text": text,
        }

        if scene_id is not None:
            line["scene_id"] = scene_id

        if shot_id is not None:
            line["shot_id"] = shot_id

        return line
