from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Final video is rendered at 25 fps via `-vsync cfr -r 25`. Each per-scene
# image duration written into scene_concat.txt is therefore rounded by
# ffmpeg to the nearest 1/25s = 0.04s frame boundary. When the rounding
# is DOWN, that scene's image plays for slightly less time than the
# matching audio segment — accumulated across N scenes this makes
# base_video shorter than merged_audio, and `-shortest` then truncates
# the tail of one or more audio segments. By ceiling-rounding each image
# duration to the next frame boundary, every scene's image is >= its
# audio segment, so the audio always plays to its natural end.
_VIDEO_FRAME_STEP_SEC = 1.0 / 25.0

def _ceil_to_frame_boundary(duration_sec: float) -> float:
    if duration_sec <= 0:
        return 0.0
    return math.ceil(duration_sec / _VIDEO_FRAME_STEP_SEC) * _VIDEO_FRAME_STEP_SEC

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class RunnerAudioRenderSupport:
    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def _effective_voice_mode(self, ctx: Any) -> str:
        voice_mode = self._runner._normalized_voice_mode(ctx.input.voice_mode)
        if voice_mode != "single":
            return voice_mode

        has_character_input = any(
            bool(str(getattr(ctx.input, field, "") or "").strip())
            for field in (
                "main_character",
                "main_character_display",
                "secondary_character",
                "secondary_character_display",
            )
        )
        has_character_profiles = bool(
            getattr(ctx.input, "character_speaker_profiles", {}) or {}
        )

        if has_character_input or has_character_profiles:
            return "character"

        return voice_mode

    def run_dialogue_script(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        voice_mode = self._effective_voice_mode(ctx)
        speaker_profiles = self._runner._speaker_profiles(ctx)

        if not ctx.input.voiceover_enabled:
            return {
                "enabled": False,
                "voice_mode": voice_mode,
                "speaker_profiles": speaker_profiles,
                "lines": [],
            }

        lines: List[Dict[str, Any]] = []

        if shot_items:
            if voice_mode == "single":
                for index, shot in enumerate(shot_items, start=1):
                    text = str(shot.get("audio_text") or shot.get("text") or "").strip()
                    if not text:
                        continue

                    lines.append(
                        {
                            "line_id": f"line_{index:02d}",
                            "shot_id": shot.get("shot_id"),
                            "scene_id": shot.get("scene_id"),
                            "speaker": "narrator",
                            "voice_style": speaker_profiles["narrator"],
                            "text": text,
                        }
                    )

                return {
                    "enabled": True,
                    "voice_mode": "single",
                    "speaker_profiles": speaker_profiles,
                    "lines": lines,
                }

            if voice_mode == "multi":
                alternating_speakers = ["mother", "child"]

                for index, shot in enumerate(shot_items, start=1):
                    text = str(shot.get("audio_text") or shot.get("text") or "").strip()
                    if not text:
                        continue

                    speaker = alternating_speakers[
                        (index - 1) % len(alternating_speakers)
                    ]
                    lines.append(
                        {
                            "line_id": f"line_{index:02d}",
                            "shot_id": shot.get("shot_id"),
                            "scene_id": shot.get("scene_id"),
                            "speaker": speaker,
                            "voice_style": speaker_profiles[speaker],
                            "text": text,
                        }
                    )

                return {
                    "enabled": True,
                    "voice_mode": "multi",
                    "speaker_profiles": speaker_profiles,
                    "lines": lines,
                }

            character_profiles = self._runner._character_speaker_profiles(ctx)
            main_character_speaker = self._runner._character_speaker_name(ctx)
            secondary_character_speaker = (
                self._runner._secondary_character_speaker_name(ctx)
            )

            for index, shot in enumerate(shot_items, start=1):
                text = str(shot.get("audio_text") or shot.get("text") or "").strip()
                if not text:
                    continue

                resolved = self._runner._resolve_character_speaker(ctx, text)

                lines.append(
                    self._runner._build_dialogue_line(
                        line_id=f"line_{index:02d}",
                        shot_id=shot.get("shot_id"),
                        scene_id=shot.get("scene_id"),
                        speaker=resolved["speaker"],
                        voice_style=resolved["voice_style"],
                        text=text,
                    )
                )

            return {
                "enabled": True,
                "voice_mode": "character",
                "speaker_profiles": {
                    "narrator": character_profiles["narrator"],
                    main_character_speaker: character_profiles["main_character"],
                    secondary_character_speaker: character_profiles[
                        "secondary_character"
                    ],
                },
                "lines": lines,
            }

        if voice_mode == "single":
            for index, scene in enumerate(scenes, start=1):
                text = str(scene.get("narration", "")).strip()
                if not text:
                    continue

                lines.append(
                    {
                        "line_id": f"line_{index:02d}",
                        "scene_id": scene.get("scene_id"),
                        "speaker": "narrator",
                        "voice_style": speaker_profiles["narrator"],
                        "text": text,
                    }
                )

            return {
                "enabled": True,
                "voice_mode": "single",
                "speaker_profiles": speaker_profiles,
                "lines": lines,
            }

        if voice_mode == "multi":
            alternating_speakers = ["mother", "child"]
            speaker_cursor = 0

            for index, scene in enumerate(scenes, start=1):
                text = str(scene.get("narration", "")).strip()
                if not text:
                    continue

                segments = [part.strip() for part in text.split("。") if part.strip()]
                if not segments:
                    segments = [text]

                for seg_index, segment in enumerate(segments, start=1):
                    speaker = alternating_speakers[
                        speaker_cursor % len(alternating_speakers)
                    ]
                    speaker_cursor += 1

                    final_text = f"{segment}。"
                    lines.append(
                        {
                            "line_id": f"line_{index:02d}_{seg_index:02d}",
                            "scene_id": scene.get("scene_id"),
                            "speaker": speaker,
                            "voice_style": speaker_profiles[speaker],
                            "text": final_text,
                        }
                    )

            return {
                "enabled": True,
                "voice_mode": "multi",
                "speaker_profiles": speaker_profiles,
                "lines": lines,
            }

        character_profiles = self._runner._character_speaker_profiles(ctx)
        main_character_speaker = self._runner._character_speaker_name(ctx)
        secondary_character_speaker = self._runner._secondary_character_speaker_name(
            ctx
        )

        for index, scene in enumerate(scenes, start=1):
            text = str(scene.get("narration", "")).strip()
            if not text:
                continue

            segments = [part.strip() for part in text.split("。") if part.strip()]
            if not segments:
                segments = [text]

            for seg_index, segment in enumerate(segments, start=1):
                final_text = f"{segment}。"
                resolved = self._runner._resolve_character_speaker(ctx, final_text)

                lines.append(
                    self._runner._build_dialogue_line(
                        line_id=f"line_{index:02d}_{seg_index:02d}",
                        scene_id=scene.get("scene_id"),
                        speaker=resolved["speaker"],
                        voice_style=resolved["voice_style"],
                        text=final_text,
                    )
                )

        return {
            "enabled": True,
            "voice_mode": "character",
            "speaker_profiles": {
                "narrator": character_profiles["narrator"],
                main_character_speaker: character_profiles["main_character"],
                secondary_character_speaker: character_profiles["secondary_character"],
            },
            "lines": lines,
        }

    def run_audio_segments(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        dialogue_script = outputs.get("dialogue_script") or {}
        lines = dialogue_script.get("lines") or []

        if not dialogue_script.get("enabled") or not lines:
            empty_directory_manifest = self._runner._write_audio_directory_manifest(
                ctx.run_id, []
            )
            return {
                "enabled": False,
                "provider": "mock_tts",
                "items": [],
                "asset_manifest": {
                    "run_id": ctx.run_id,
                    "provider": "mock_tts",
                    "asset_count": 0,
                    "assets": [],
                },
                "directory_manifest": empty_directory_manifest,
                "scene_asset_map": [],
            }

        items: List[Dict[str, Any]] = []
        assets: List[Dict[str, Any]] = []
        run_dir = self._runner._ensure_audio_run_dir(ctx.run_id)

        tts_enabled = self._runner._tts_enabled()
        fallback_to_mock = self._runner._tts_fallback_to_mock()
        real_generation_count = 0

        for index, line in enumerate(lines, start=1):
            text = str(line.get("text", "")).strip()
            speaker = str(line.get("speaker", "narrator"))
            voice_style = str(line.get("voice_style", ctx.input.voice_style))
            scene_id = line.get("scene_id")
            shot_id = line.get("shot_id")

            char_count = max(1, len(text))
            # Chinese children's story TTS narrates at ~5.1 chars/sec
            # (measured empirically). The story plan targets:
            # 280/60s, 610/120s, 920/180s.
            # Using 5.0 as the estimate so the ±30% speed-retry threshold is
            # not triggered on normal narration segments and speed adjustment
            # stays a fine-tune.
            duration_estimate_sec = max(2, min(20, round(char_count / 5)))
            duration_sec = float(duration_estimate_sec)
            duration_source = "estimate"

            file_name = f"{speaker}_{index:02d}.mp3"
            relative_path = f"assets/mock/audio/{ctx.run_id}/{file_name}"
            public_url = f"/assets/mock/audio/{ctx.run_id}/{file_name}"
            output_path = run_dir / file_name
            waveform_preview = [
                max(0.12, round(duration_sec / 12, 2)),
                0.48,
                0.76,
                0.35,
                0.62,
            ]

            generation_provider = "mock_tts"
            generation_status = "planned"
            asset_status = "mock_registered"
            generation_mode = "placeholder_manifest_only"
            asset_metadata: Dict[str, Any] = {}
            error_message: Optional[str] = None

            if tts_enabled:
                try:
                    tts_result = self._runner._generate_real_tts_audio(
                        text=text,
                        speaker=speaker,
                        voice_style=voice_style,
                        output_path=output_path,
                    )
                    generation_provider = str(
                        tts_result.get("provider", self._runner._tts_provider_name())
                    )
                    generation_status = "generated"
                    asset_status = "generated"
                    generation_mode = "real_tts"

                    actual_duration_sec = self._runner._probe_audio_duration_seconds(
                        output_path
                    )
                    if actual_duration_sec is not None:
                        duration_sec = actual_duration_sec
                        duration_source = "ffprobe"

                    # Speed adjustment: if actual duration deviates significantly
                    # from the char-count estimate, re-generate at an adjusted
                    # speed. Content (text) is never changed here — only TTS rate.
                    # Story-level text expansion/compression happens earlier in
                    # run_story() via story_retry_policy before images are generated.
                    #
                    # Skip speed adjustment when the story came from template_fallback.
                    # Template text is pre-calibrated to the target duration, so
                    # adjusting speed here would only compound the calibration and
                    # produce a shorter video than intended.
                    story_generation_source = str(
                        (outputs.get("story") or {}).get("generation_source") or ""
                    )
                    speed_adjustment_allowed = story_generation_source != "template_fallback"
                    duration_retry_meta: Dict[str, Any] = {}
                    if actual_duration_sec is not None and duration_estimate_sec > 0 and speed_adjustment_allowed:
                        retry_speed: Optional[float] = None
                        if actual_duration_sec < duration_estimate_sec * 0.70:
                            # Too short: slow down to fill the scene slot.
                            # Slow-down is safe — TTS providers handle
                            # speed<1 by stretching audio (more padding
                            # or syllable extension), no content loss.
                            ratio = actual_duration_sec / duration_estimate_sec
                            retry_speed = max(0.75, min(0.95, ratio))
                        # NO speed-up retry here. Empirically TTS providers
                        # (SiliconFlow / OpenAI-compatible) drop trailing
                        # syllables when handed speed>1 — the last word /
                        # particle of long sentences vanishes ("个别句子
                        # 尾音消失"). The global speedup pass at the end
                        # of this method (uniform across ALL segments)
                        # still handles total-duration overshoot, so
                        # losing per-segment speed-up is no functional
                        # regression — only a correctness fix.

                        if retry_speed is not None:
                            try:
                                retry_result = self._runner._generate_real_tts_audio(
                                    text=text,
                                    speaker=speaker,
                                    voice_style=voice_style,
                                    output_path=output_path,
                                    speed=retry_speed,
                                )
                                retry_duration = self._runner._probe_audio_duration_seconds(
                                    output_path
                                )
                                improved = (
                                    retry_duration is not None
                                    and (
                                        (retry_speed < 1.0 and retry_duration > actual_duration_sec)
                                        or (retry_speed > 1.0 and retry_duration < actual_duration_sec)
                                    )
                                )
                                if improved:
                                    duration_sec = retry_duration
                                    duration_source = "ffprobe_speed_retry"
                                    duration_retry_meta = {
                                        "duration_retry": True,
                                        "retry_speed": retry_speed,
                                        "original_duration_sec": actual_duration_sec,
                                        "retry_duration_sec": retry_duration,
                                        "retry_output_bytes": retry_result.get("output_bytes"),
                                    }
                                else:
                                    # Speed retry didn't improve — restore original
                                    self._runner._generate_real_tts_audio(
                                        text=text,
                                        speaker=speaker,
                                        voice_style=voice_style,
                                        output_path=output_path,
                                    )
                                    duration_retry_meta = {
                                        "duration_retry": False,
                                        "retry_speed": retry_speed,
                                    }
                            except Exception:
                                duration_retry_meta = {
                                    "duration_retry": False,
                                    "retry_error": True,
                                }

                    asset_metadata = {
                        "tts_model": tts_result.get("model"),
                        "tts_voice": tts_result.get("voice"),
                        "output_bytes": tts_result.get("output_bytes"),
                        "duration_source": duration_source,
                        **duration_retry_meta,
                    }
                    real_generation_count += 1
                except Exception as e:
                    error_message = str(e)
                    if not fallback_to_mock:
                        raise RuntimeError(
                            f"audio segment generation failed at line {index}: {error_message}"
                        ) from e

                    generation_provider = "mock_tts"
                    generation_status = "planned"
                    asset_status = "mock_registered"
                    generation_mode = "placeholder_manifest_only"
                    asset_metadata = {
                        "fallback_reason": error_message,
                    }
            else:
                asset_metadata = {
                    "fallback_reason": "TTS_ENABLED is false",
                }

            asset = {
                "asset_id": f"audio_asset_{index:02d}",
                "segment_id": f"audio_{index:02d}",
                "shot_id": shot_id,
                "scene_id": scene_id,
                "speaker": speaker,
                "voice_style": voice_style,
                "provider": generation_provider,
                "file_name": file_name,
                "relative_path": relative_path,
                "public_url": public_url,
                "mime_type": "audio/mpeg",
                "duration_estimate_sec": duration_estimate_sec,
                "duration_sec": duration_sec,
                "duration_source": duration_source,
                "asset_status": asset_status,
                "generation_mode": generation_mode,
                "waveform_preview": waveform_preview,
                "metadata": asset_metadata,
            }

            item = {
                "segment_id": f"audio_{index:02d}",
                "shot_id": shot_id,
                "scene_id": scene_id,
                "speaker": speaker,
                "text": text,
                "voice_style": voice_style,
                "target_audio_file": relative_path,
                "duration_estimate_sec": duration_estimate_sec,
                "duration_sec": duration_sec,
                "duration_source": duration_source,
                "provider": generation_provider,
                "status": generation_status,
                "asset_public_url": public_url,
                "mock_asset": asset,
            }

            if error_message:
                item["error"] = error_message

            items.append(item)
            assets.append(asset)

        directory_manifest = self._runner._write_audio_directory_manifest(
            ctx.run_id, assets
        )
        scene_asset_map = self._runner._group_audio_assets_by_scene(assets)

        overall_provider = (
            self._runner._tts_provider_name()
            if real_generation_count > 0
            else "mock_tts"
        )

        total_duration_sec = sum(float(item.get("duration_sec") or 0) for item in items)
        target_duration_sec = float(getattr(ctx.input, "duration_sec", 0) or 0)
        duration_too_short = (
            target_duration_sec > 0
            and real_generation_count > 0
            and total_duration_sec < target_duration_sec * 0.80
        )
        duration_summary = {
            "total_duration_sec": round(total_duration_sec, 2),
            "target_duration_sec": target_duration_sec,
            "duration_gap_sec": round(max(0.0, target_duration_sec - total_duration_sec), 2),
            "duration_too_short": duration_too_short,
        }
        if duration_too_short:
            duration_summary["warning"] = (
                f"audio total {total_duration_sec:.1f}s is shorter than "
                f"80% of target {target_duration_sec:.0f}s; "
                "consider expanding narration text"
            )

        # Total-duration speedup: when the LLM compression retry from
        # story_retry_policy didn't bring the story fully under target
        # (common case — LLM lands at ~110% of target), re-render the
        # real TTS segments at a higher speed so the final video lands
        # on the user's selected duration.
        # Skipped for template_fallback (template text is pre-calibrated
        # to target so speeding it up would undershoot).
        # Cap at 1.5× to keep narration listenable for children content.
        story_generation_source = str(
            (outputs.get("story") or {}).get("generation_source") or ""
        )
        # 1.05 threshold: TTS natural rendering varies by ±3-5%, so anything
        # within that range is treated as on-target. Beyond 5% overshoot
        # triggers the speedup pass.
        duration_too_long = (
            target_duration_sec > 0
            and real_generation_count > 0
            and total_duration_sec > target_duration_sec * 1.05
            and story_generation_source != "template_fallback"
            and tts_enabled
        )
        duration_summary["duration_too_long"] = duration_too_long

        if duration_too_long:
            desired_speedup = total_duration_sec / target_duration_sec
            speedup_factor = round(min(1.5, max(1.05, desired_speedup)), 3)
            new_total = 0.0
            adjusted_count = 0
            for item, asset in zip(items, assets):
                # Only the real TTS path is worth re-rendering; mock /
                # placeholder segments have no rendered audio to speed up.
                if asset.get("generation_mode") != "real_tts":
                    new_total += float(item.get("duration_sec") or 0)
                    continue
                file_name = asset.get("file_name") or ""
                if not file_name:
                    new_total += float(item.get("duration_sec") or 0)
                    continue
                seg_output_path = run_dir / file_name
                try:
                    self._runner._generate_real_tts_audio(
                        text=str(item.get("text", "")),
                        speaker=str(item.get("speaker", "narrator")),
                        voice_style=str(item.get("voice_style", ctx.input.voice_style)),
                        output_path=seg_output_path,
                        speed=speedup_factor,
                    )
                    new_duration = self._runner._probe_audio_duration_seconds(
                        seg_output_path
                    )
                    if new_duration is not None and new_duration > 0:
                        item["duration_sec"] = float(new_duration)
                        item["duration_source"] = "ffprobe_total_speedup"
                        asset["duration_sec"] = float(new_duration)
                        asset["duration_source"] = "ffprobe_total_speedup"
                        meta = asset.get("metadata") or {}
                        meta["total_speedup_factor"] = speedup_factor
                        meta["duration_source"] = "ffprobe_total_speedup"
                        asset["metadata"] = meta
                        new_total += float(new_duration)
                        adjusted_count += 1
                    else:
                        new_total += float(item.get("duration_sec") or 0)
                except Exception as error:
                    # Single-segment TTS failure shouldn't break the run —
                    # keep the original (pre-speedup) audio for that segment.
                    print(
                        f"[audio_render] speedup retry failed for {file_name}: {error}"
                    )
                    new_total += float(item.get("duration_sec") or 0)

            total_duration_sec = new_total
            duration_summary["total_duration_sec"] = round(new_total, 2)
            duration_summary["global_speedup_factor"] = speedup_factor
            duration_summary["speedup_segments_adjusted"] = adjusted_count
            duration_summary["duration_gap_sec"] = round(
                max(0.0, target_duration_sec - new_total), 2
            )

        return {
            "enabled": True,
            "provider": overall_provider,
            "items": items,
            "asset_manifest": {
                "run_id": ctx.run_id,
                "provider": overall_provider,
                "asset_count": len(assets),
                "generated_count": real_generation_count,
                "assets": assets,
            },
            "directory_manifest": directory_manifest,
            "scene_asset_map": scene_asset_map,
            "duration_summary": duration_summary,
        }

    def run_narration(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        dialogue_script = outputs.get("dialogue_script") or {}
        dialogue_lines = dialogue_script.get("lines") or []

        if dialogue_script.get("enabled") and dialogue_lines:
            segments: List[Dict[str, Any]] = []
            full_text_parts: List[str] = []

            for line in dialogue_lines:
                text = str(line.get("text", ""))
                speaker = str(line.get("speaker", "narrator"))
                voice_style = str(line.get("voice_style", ctx.input.voice_style))
                scene_id = line.get("scene_id")

                full_text_parts.append(f"[{speaker}] {text}")
                segments.append(
                    {
                        "scene_id": scene_id,
                        "speaker": speaker,
                        "text": text,
                        "voice_style": voice_style,
                    }
                )

            return {
                "voice_style": ctx.input.voice_style,
                "language": ctx.input.language,
                "voiceover_enabled": True,
                "voice_mode": dialogue_script.get("voice_mode", "single"),
                "full_text": "\n".join(full_text_parts),
                "segments": segments,
            }

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        segments: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        for scene in scenes:
            text = str(scene.get("narration", ""))
            full_text_parts.append(text)
            segments.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "speaker": "narrator",
                    "text": text,
                    "voice_style": ctx.input.voice_style,
                }
            )

        return {
            "voice_style": ctx.input.voice_style,
            "language": ctx.input.language,
            "voiceover_enabled": False,
            "voice_mode": "single",
            "full_text": "\n".join(full_text_parts),
            "segments": segments,
        }

    def run_subtitles(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        if not ctx.input.subtitle_enabled:
            return {"enabled": False, "items": [], "srt_preview": ""}

        audio_segments = outputs.get("audio_segments") or {}
        items_source = audio_segments.get("items") or []

        # ---- fallback: silent 场景也要能生成字幕（用 storyboard.scenes 驱动时间轴）----
        if not items_source:
            storyboard = outputs.get("storyboard") or {}
            scenes = storyboard.get("scenes") or []
            if isinstance(scenes, list) and scenes:
                synthesized = []
                for scene in scenes:
                    if not isinstance(scene, dict):
                        continue
                    text = str(scene.get("narration") or "").strip()
                    if not text:
                        continue
                    duration_sec = float(scene.get("duration_sec") or 0.0)
                    if duration_sec <= 0:
                        duration_sec = 3.0
                    synthesized.append(
                        {
                            "text": text,
                            "duration_sec": duration_sec,
                            "scene_id": scene.get("scene_id"),
                            "shot_id": scene.get("shot_id"),
                        }
                    )
                items_source = synthesized

        items: List[Dict[str, Any]] = []
        current_start = 0.0
        srt_lines: List[str] = []

        def _format_srt_time(total_seconds: float) -> str:
            millis = int(round(total_seconds * 1000))
            hours = millis // 3600000
            millis %= 3600000
            minutes = millis // 60000
            millis %= 60000
            seconds = millis // 1000
            millis %= 1000
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        for index, segment in enumerate(items_source, start=1):
            text = str(segment.get("text", "")).strip()
            if not text:
                continue

            duration_sec = float(segment.get("duration_sec") or 0.0)
            if duration_sec <= 0:
                duration_sec = float(segment.get("duration_estimate_sec") or 3.0)
            if duration_sec <= 0:
                duration_sec = 3.0

            start_sec = current_start
            end_sec = current_start + duration_sec
            current_start = end_sec

            item = {
                "index": index,
                "shot_id": segment.get("shot_id"),
                "scene_id": segment.get("scene_id"),
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": text,
            }
            items.append(item)

            srt_lines.extend(
                [
                    str(index),
                    f"{_format_srt_time(start_sec)} --> {_format_srt_time(end_sec)}",
                    text,
                    "",
                ]
            )

        return {
            "enabled": True,
            "items": items,
            "srt_preview": "\n".join(srt_lines).strip(),
        }

    def build_video_concat_file(
        self,
        ctx: Any,
        image_assets: Dict[str, Any],
        audio_segments: Dict[str, Any],
    ) -> Path:
        image_assets_list = image_assets.get("assets") or []
        audio_items = audio_segments.get("items") or []

        image_by_shot = {
            str(item.get("shot_id")): item
            for item in image_assets_list
            if item.get("shot_id")
        }
        image_by_scene = {
            str(item.get("scene_id")): item
            for item in image_assets_list
            if item.get("scene_id")
        }
        print("image_assets_list len =", len(image_assets_list))
        print("audio_items len =", len(audio_items))
        concat_lines: List[str] = []
        video_run_dir = self._runner._ensure_video_run_dir(ctx.run_id)
        concat_file = video_run_dir / "scene_concat.txt"
        last_image_path: Optional[Path] = None

        # 如果有音频，用音频驱动时长
        if audio_items:
            loop_items = audio_items
        else:
            # 无音频时，用图片列表驱动
            loop_items = image_assets_list

        for item in loop_items:
            shot_id = str(item.get("shot_id") or "")
            scene_id = str(item.get("scene_id") or "")

            image_asset = None
            if shot_id:
                image_asset = image_by_shot.get(shot_id)
            if image_asset is None and scene_id:
                image_asset = image_by_scene.get(scene_id)
            if image_asset is None and not audio_items:
                # 无音频时 item 本身就是 image_asset
                image_asset = item

            if image_asset is None:
                continue

            selected_asset_ref = image_asset.get("selected_asset_ref") or {}
            resolved_relative_path = ""

            if isinstance(selected_asset_ref, dict) and selected_asset_ref:
                resolved_relative_path = str(
                    selected_asset_ref.get("relative_path") or ""
                ).strip()

            if not resolved_relative_path:
                resolved_relative_path = str(
                    image_asset.get("relative_path") or ""
                ).strip()

            if not resolved_relative_path:
                continue

            image_path = PROJECT_ROOT / resolved_relative_path

            if audio_items:
                duration_sec = float(item.get("duration_sec") or 0.0)
                if duration_sec <= 0:
                    duration_sec = float(item.get("duration_estimate_sec") or 3.0)
            else:
                duration_sec = float(image_asset.get("duration_sec") or 0.0)
                if duration_sec <= 0:
                    duration_sec = float(
                        image_asset.get("duration_estimate_sec") or 0.0
                    )
                if duration_sec <= 0:
                    duration_sec = float(ctx.input.duration_sec) / max(
                        len(image_assets_list), 1
                    )

            # Ceiling-round to the next 25 fps frame boundary so the image
            # is shown for at least as long as the matching audio segment.
            # See _ceil_to_frame_boundary docstring above the helper for
            # the full rationale (tail-clipping symptom).
            duration_sec = _ceil_to_frame_boundary(duration_sec)

            escaped_image_path = str(image_path).replace("'", "'\\''")
            concat_lines.append(f"file '{escaped_image_path}'")
            concat_lines.append(f"duration {duration_sec:.3f}")
            last_image_path = image_path
        if last_image_path is not None:
            escaped_last_image_path = str(last_image_path).replace("'", "'\\''")
            concat_lines.append(f"file '{escaped_last_image_path}'")

        concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
        return concat_file

    def run_final_video(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        image_assets = outputs.get("image_assets") or {}
        audio_segments = outputs.get("audio_segments") or {}
        subtitles = outputs.get("subtitles") or {}

        raw_asset_list = image_assets.get("assets") or []
        audio_item_list = audio_segments.get("items") or []

        # Partition assets. Failed placeholders (from B1) have
        # status='failed' and no relative_path — they must never reach
        # ffmpeg or it crashes on the missing file.
        usable_asset_list: List[Dict[str, Any]] = []
        failed_scene_ids: List[str] = []
        for asset in raw_asset_list:
            if not isinstance(asset, dict):
                continue
            status = str(asset.get("status") or "").strip().lower()
            if status == "failed" or not asset.get("relative_path"):
                scene_id = str(asset.get("scene_id") or "").strip()
                if scene_id:
                    failed_scene_ids.append(scene_id)
                continue
            usable_asset_list.append(asset)

        # Render gate: if ANY scene failed, refuse to produce a final
        # video. The previous "render with what we have and mark
        # degraded" approach silently shipped incomplete videos and
        # made the review UI think the run was done (videoGenerated =
        # true → per-scene retry button hidden → user trapped). The
        # correct invariant is `final_video.public_url exists ⟺ every
        # scene succeeded`; until the user retries the failed scenes,
        # there is no final video at all. The blocked status surfaces
        # missing_scene_ids so the UI can show actionable error copy
        # ("X 个场景生成失败，请重试后再渲染") instead of a fake "done"
        # state.
        if failed_scene_ids:
            return {
                "enabled": False,
                "status": "blocked",
                "reason": "missing_images",
                "missing_scene_ids": failed_scene_ids,
                "rendered_scene_count": 0,
            }

        image_asset_list = usable_asset_list

        if not image_asset_list:
            return {
                "enabled": False,
                "status": "skipped",
                "reason": "missing image_assets",
                "missing_scene_ids": failed_scene_ids,
            }

        # ========= 计算总时长 =========
        total_duration_sec = 0.0
        if audio_item_list:
            for item in audio_item_list:
                duration_sec = float(item.get("duration_sec") or 0.0)
                if duration_sec <= 0:
                    duration_sec = float(item.get("duration_estimate_sec") or 0.0)
                total_duration_sec += max(duration_sec, 0.0)
        else:
            for item in image_asset_list:
                duration_sec = float(item.get("duration_sec") or 0.0)
                if duration_sec <= 0:
                    duration_sec = float(item.get("duration_estimate_sec") or 0.0)
                total_duration_sec += max(duration_sec, 0.0)

            if total_duration_sec <= 0:
                total_duration_sec = float(ctx.input.duration_sec)

        video_run_dir = self._runner._ensure_video_run_dir(ctx.run_id)

        # ========= 生成 base video =========
        # Pass a filtered image_assets dict so the concat builder never
        # sees failed placeholders (their relative_path is None and
        # would otherwise crash ffmpeg).
        usable_image_assets = {**image_assets, "assets": image_asset_list}
        concat_file = self.build_video_concat_file(ctx, usable_image_assets, audio_segments)

        base_video_path = video_run_dir / "base_video.mp4"

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-vsync",
                "cfr",
                "-r",
                "25",
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                str(base_video_path),
            ],
            check=True,
        )

        # ========= 判断是否真的有音频文件 =========
        audio_manifest = audio_segments.get("asset_manifest") or {}
        audio_assets = audio_manifest.get("assets") or []

        audio_file_paths: List[str] = []
        for asset in audio_assets:
            relative_path = str(asset.get("relative_path") or "").strip()
            if not relative_path:
                continue
            full_path = PROJECT_ROOT / relative_path
            if full_path.exists():
                audio_file_paths.append(str(full_path))

        has_audio = len(audio_file_paths) > 0

        merged_audio_path = None

        # ========= 有音频才 concat =========
        if has_audio:
            merged_audio_path = video_run_dir / "merged_audio.mp3"
            merged_audio_list_path = video_run_dir / "merged_audio_inputs.txt"

            concat_audio_lines = []
            for path in audio_file_paths:
                escaped_path = path.replace("'", "'\\''")
                concat_audio_lines.append(f"file '{escaped_path}'")

            merged_audio_list_path.write_text(
                "\n".join(concat_audio_lines) + "\n",
                encoding="utf-8",
            )

            # Sample-accurate concat via the `concat` FILTER (not the
            # concat demuxer). The demuxer approach (`-f concat`) plus
            # re-encode mis-handles LAME's per-file priming/padding
            # metadata, which can cut real audio samples at segment
            # tails ("尾音被吃"). The filter approach feeds each MP3 as
            # a separate input, decodes each fully to PCM, explicitly
            # concatenates the sample arrays, then re-encodes ONCE — no
            # sample loss at boundaries AND no MP3 bit-reservoir issues
            # at the resulting concat points.
            #
            # 128 kbps preserves perceived TTS quality (TTS providers
            # typically deliver 64–128 kbps).
            ffmpeg_concat_cmd: List[str] = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
            ]
            for seg_path in audio_file_paths:
                ffmpeg_concat_cmd.extend(["-i", seg_path])
            n_segments = len(audio_file_paths)
            filter_inputs = "".join(f"[{i}:a]" for i in range(n_segments))
            filter_expr = f"{filter_inputs}concat=n={n_segments}:v=0:a=1[out]"
            ffmpeg_concat_cmd.extend(
                [
                    "-filter_complex",
                    filter_expr,
                    "-map",
                    "[out]",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    str(merged_audio_path),
                ]
            )
            subprocess.run(ffmpeg_concat_cmd, check=True)

        # ========= 写字幕 =========
        subtitle_path = video_run_dir / "subtitles.srt"
        srt_text = str(subtitles.get("srt_preview", "") or "").strip()

        if srt_text:
            subtitle_path.write_text(srt_text + "\n", encoding="utf-8")
        else:
            # silent/skip subtitles 时，避免留下只有 '\n' 的“假非空字幕文件”
            if subtitle_path.exists():
                subtitle_path.unlink()

        # ========= 合成 final =========
        final_video_path = video_run_dir / "final.mp4"

        # ====== 若字幕时间轴超过视频时长：按比例压缩到 base_video 实际时长（silent/有声都适用）======
        def _ffprobe_duration_sec(video_path: Path) -> float:
            try:
                out = subprocess.check_output(
                    [
                        "ffprobe",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        str(video_path),
                    ],
                    text=True,
                ).strip()
                return float(out) if out else 0.0
            except Exception:
                return 0.0

        def _parse_ts(ts: str) -> float:
            hh, mm, rest = ts.split(":")
            ss, ms = rest.split(",")
            return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0

        def _fmt_ts(sec: float) -> str:
            if sec < 0:
                sec = 0.0
            ms = int(round((sec - int(sec)) * 1000))
            total = int(sec)
            hh = total // 3600
            mm = (total % 3600) // 60
            ss = total % 60
            return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

        def _rescale_srt_to_duration(srt_path: Path, target_duration: float) -> None:
            if target_duration <= 0:
                return
            if not srt_path.exists():
                return
            txt = srt_path.read_text(encoding="utf-8", errors="ignore")
            if not txt.strip():
                return

            lines = txt.splitlines()
            last_end = 0.0
            for line in lines:
                if "-->" in line:
                    try:
                        end = line.split("-->")[1].strip()
                        last_end = max(last_end, _parse_ts(end))
                    except Exception:
                        pass

            # 已经不超过视频时长就不处理
            if last_end <= 0 or last_end <= target_duration + 0.01:
                return

            scale = target_duration / last_end

            out_lines = []
            for line in lines:
                if "-->" not in line:
                    out_lines.append(line)
                    continue
                try:
                    a, b = line.split("-->")
                    start = _parse_ts(a.strip()) * scale
                    end = _parse_ts(b.strip()) * scale
                    if end <= start:
                        end = start + 0.2
                    out_lines.append(f"{_fmt_ts(start)} --> {_fmt_ts(end)}")
                except Exception:
                    out_lines.append(line)

            srt_path.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")

        video_duration = _ffprobe_duration_sec(base_video_path)
        _rescale_srt_to_duration(subtitle_path, video_duration)

        # The `-t` cap below was using `total_duration_sec`, which is the
        # SUM of each individual MP3's ffprobe duration. The actual
        # merged_audio.mp3 (built by `ffmpeg -f concat -c copy`) can be a
        # few tens of ms LONGER than that sum because of MP3 frame
        # boundary alignment — the last syllable of the final segment
        # then gets clipped by `-t`. Probe the merged file's real length
        # and add a small safety buffer so the cap never sits inside an
        # active audio frame.
        if has_audio and merged_audio_path:
            actual_audio_duration = _ffprobe_duration_sec(merged_audio_path)
            if actual_audio_duration > 0:
                total_duration_sec = max(total_duration_sec, actual_audio_duration) + 0.2

        # Subtitle file may be missing (silent or skipped subtitles). The
        # `-vf subtitles=...` filter fails hard when the .srt path
        # doesn't exist on disk → ffmpeg exits 254 → render endpoint
        # returns 500. The no-audio branch below already guards on this;
        # the audio branch must do the same.
        subtitle_available = (
            subtitle_path.exists() and subtitle_path.stat().st_size > 0
        )

        if has_audio and merged_audio_path:
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(base_video_path),
                "-i",
                str(merged_audio_path),
                "-t",
                f"{total_duration_sec:.3f}",
            ]
            if subtitle_available:
                escaped_subtitle_path = (
                    str(subtitle_path)
                    .replace("\\", "\\\\")
                    .replace(":", "\\:")
                    .replace("'", "\\'")
                )
                ffmpeg_cmd.extend(["-vf", f"subtitles='{escaped_subtitle_path}'"])
            else:
                print("[final-video] subtitle file missing or empty, skip subtitles (audio branch)")
            ffmpeg_cmd.extend(
                [
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(final_video_path),
                ]
            )
            subprocess.run(ffmpeg_cmd, check=True)
        else:
            # 如果字幕文件不存在或为空，就不要加字幕滤镜
            if subtitle_path.exists() and subtitle_path.stat().st_size > 0:
                escaped_subtitle_path = (
                    str(subtitle_path)
                    .replace("\\", "\\\\")
                    .replace(":", "\\:")
                    .replace("'", "\\'")
                )
                subtitle_filter = f"subtitles='{escaped_subtitle_path}'"

                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(base_video_path),
                        "-t",
                        f"{total_duration_sec:.3f}",
                        "-vf",
                        subtitle_filter,
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        str(final_video_path),
                    ],
                    check=True,
                )
            else:
                print("[final-video] subtitle file missing or empty, skip subtitles")

                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(base_video_path),
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        str(final_video_path),
                    ],
                    check=True,
                )
        final_video_duration_sec = _ffprobe_duration_sec(final_video_path)

        # ========= 统一 return =========
        # The render gate above guarantees we only reach here when
        # every scene succeeded, so status is unambiguously
        # 'generated'. rendered_scene_count is still useful as
        # downstream telemetry / sanity check.
        return {
            "enabled": True,
            "status": "generated",
            "rendered_scene_count": len(image_asset_list),
            "run_id": ctx.run_id,
            "file_name": "final.mp4",
            "relative_path": f"assets/mock/video/{ctx.run_id}/final.mp4",
            "public_url": f"/assets/mock/video/{ctx.run_id}/final.mp4",
            "duration_sec": round(total_duration_sec, 3),
            "actual_duration_sec": round(final_video_duration_sec, 3),
            "base_video_duration_sec": round(video_duration, 3),
            "audio_track_path": (
                f"assets/mock/video/{ctx.run_id}/merged_audio.mp3"
                if has_audio
                else None
            ),
            "subtitle_path": f"assets/mock/video/{ctx.run_id}/subtitles.srt",
            "audio_enabled": has_audio,
            "audio_mode": "tts" if has_audio else "silent",
        }

    def rerender_final_video(
        self,
        *,
        workflow_id: str,
        session_id: Optional[str],
        run_id: str,
        workflow_input: Dict[str, Any],
        image_assets: Dict[str, Any],
        audio_segments: Dict[str, Any],
        subtitles: Dict[str, Any],
    ) -> Dict[str, Any]:
        ctx_input = self._runner._workflow_input_from_dict(workflow_input)
        ctx = self._runner._build_step_context(
            workflow_id=workflow_id,
            session_id=session_id,
            run_id=run_id,
            workflow_input=ctx_input,
        )

        final_video = self.run_final_video(
            ctx,
            {
                "image_assets": image_assets,
                "audio_segments": audio_segments,
                "subtitles": subtitles,
            },
        )

        return {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "run_id": run_id,
            "final_video": final_video,
        }
