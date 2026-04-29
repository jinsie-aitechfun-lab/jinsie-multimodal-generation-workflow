from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


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

    def run_dialogue_script(
        self, ctx: Any, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            secondary_character_speaker = self._runner._secondary_character_speaker_name(ctx)

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
                    secondary_character_speaker: character_profiles["secondary_character"],
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
        secondary_character_speaker = self._runner._secondary_character_speaker_name(ctx)

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

    def run_audio_segments(
        self, ctx: Any, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            duration_estimate_sec = max(2, min(12, char_count // 8))
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

                    actual_duration_sec = self._runner._probe_audio_duration_seconds(output_path)
                    if actual_duration_sec is not None:
                        duration_sec = actual_duration_sec
                        duration_source = "ffprobe"

                    asset_metadata = {
                        "tts_model": tts_result.get("model"),
                        "tts_voice": tts_result.get("voice"),
                        "output_bytes": tts_result.get("output_bytes"),
                        "duration_source": duration_source,
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

        directory_manifest = self._runner._write_audio_directory_manifest(ctx.run_id, assets)
        scene_asset_map = self._runner._group_audio_assets_by_scene(assets)

        overall_provider = (
            self._runner._tts_provider_name() if real_generation_count > 0 else "mock_tts"
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
        }

    def run_narration(
        self, ctx: Any, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
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

    def run_subtitles(
        self, ctx: Any, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not ctx.input.subtitle_enabled:
            return {"enabled": False, "items": [], "srt_preview": ""}

        audio_segments = outputs.get("audio_segments") or {}
        items_source = audio_segments.get("items") or []

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

        concat_lines: List[str] = []
        video_run_dir = self._runner._ensure_video_run_dir(ctx.run_id)
        concat_file = video_run_dir / "scene_concat.txt"
        last_image_path: Optional[Path] = None

        for item in audio_items:
            shot_id = str(item.get("shot_id") or "")
            scene_id = str(item.get("scene_id") or "")

            image_asset = None
            if shot_id:
                image_asset = image_by_shot.get(shot_id)
            if image_asset is None and scene_id:
                image_asset = image_by_scene.get(scene_id)
            if image_asset is None:
                continue

            selected_asset_ref = image_asset.get("selected_asset_ref") or {}
            resolved_relative_path = ""

            if isinstance(selected_asset_ref, dict) and selected_asset_ref:
                resolved_relative_path = str(selected_asset_ref.get("relative_path") or "").strip()

            if not resolved_relative_path:
                resolved_relative_path = str(image_asset.get("relative_path") or "").strip()

            if not resolved_relative_path:
                continue

            image_path = PROJECT_ROOT / resolved_relative_path
            duration_sec = float(item.get("duration_sec") or 0.0)
            if duration_sec <= 0:
                duration_sec = float(item.get("duration_estimate_sec") or 3.0)
            if duration_sec <= 0:
                duration_sec = 3.0

            escaped_image_path = str(image_path).replace("'", "'\\''")
            concat_lines.append(f"file '{escaped_image_path}'")
            concat_lines.append(f"duration {duration_sec:.3f}")
            last_image_path = image_path

        if last_image_path is not None:
            escaped_last_image_path = str(last_image_path).replace("'", "'\\''")
            concat_lines.append(f"file '{escaped_last_image_path}'")

        concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
        return concat_file

    def run_final_video(
        self, ctx: Any, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        image_assets = outputs.get("image_assets") or {}
        audio_segments = outputs.get("audio_segments") or {}
        subtitles = outputs.get("subtitles") or {}

        image_asset_list = image_assets.get("assets") or []
        audio_item_list = audio_segments.get("items") or []

        if not image_asset_list:
            return {
                "enabled": False,
                "status": "skipped",
                "reason": "missing image_assets",
            }

        # ========= 计算总时长 =========
        total_duration_sec = 0.0
        for item in audio_item_list:
            duration_sec = float(item.get("duration_sec") or 0.0)
            if duration_sec <= 0:
                duration_sec = float(item.get("duration_estimate_sec") or 0.0)
            total_duration_sec += max(duration_sec, 0.0)

        video_run_dir = self._runner._ensure_video_run_dir(ctx.run_id)

        # ========= 生成 base video =========
        concat_file = self.build_video_concat_file(
            ctx, image_assets, audio_segments
        )

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

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(merged_audio_list_path),
                    "-c",
                    "copy",
                    str(merged_audio_path),
                ],
                check=True,
            )

        # ========= 写字幕 =========
        subtitle_path = video_run_dir / "subtitles.srt"
        subtitle_path.write_text(
            str(subtitles.get("srt_preview", "")).strip() + "\n",
            encoding="utf-8",
        )

        # ========= 合成 final =========
        final_video_path = video_run_dir / "final.mp4"

        if has_audio and merged_audio_path:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(base_video_path),
                    "-i",
                    str(merged_audio_path),
                    "-vf",
                    f"subtitles={subtitle_path}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(final_video_path),
                ],
                check=True,
            )
        else:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(base_video_path),
                    "-vf",
                    f"subtitles={subtitle_path}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(final_video_path),
                ],
                check=True,
            )

        # ========= 统一 return =========
        return {
            "enabled": True,
            "status": "generated",
            "run_id": ctx.run_id,
            "file_name": "final.mp4",
            "relative_path": f"assets/mock/video/{ctx.run_id}/final.mp4",
            "public_url": f"/assets/mock/video/{ctx.run_id}/final.mp4",
            "duration_sec": round(total_duration_sec, 3),
            "audio_track_path": (
                f"assets/mock/video/{ctx.run_id}/merged_audio.mp3"
                if has_audio else None
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