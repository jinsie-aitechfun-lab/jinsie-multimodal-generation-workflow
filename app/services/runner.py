from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import uuid4
from xml.sax.saxutils import escape as xml_escape

from app.schemas.workflow import (
    StepResult,
    WorkflowInput,
    WorkflowRunRequest,
    WorkflowRunResponse,
)


class UnknownStepError(Exception):
    pass


class UnknownVideoProviderError(Exception):
    pass


@dataclass(frozen=True)
class StepContext:
    workflow_id: str
    session_id: Optional[str]
    run_id: str
    input: WorkflowInput


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MOCK_AUDIO_ROOT = PROJECT_ROOT / "assets" / "mock" / "audio"
MOCK_IMAGE_ROOT = PROJECT_ROOT / "assets" / "mock" / "image"
MOCK_VIDEO_ROOT = PROJECT_ROOT / "assets" / "mock" / "video"

DEFAULT_TTS_API_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TTS_PROVIDER = "openai_compatible_tts"
DEFAULT_IMAGE_PROVIDER = "pillow_storybook_renderer"
DEFAULT_IMAGE_FALLBACK_PROVIDER = "pillow_storybook_renderer"


class WorkflowRunner:
    """
    Phase 1 upgrade:
    - move from simple demo workflow to structured story-video generation workflow
    - keep placeholder generation style, but upgrade protocol and outputs
    - support default parameters for topic-driven generation

    Phase 1 quality refinement:
    - generate more natural Chinese story text
    - produce non-duplicated storyboard scenes

    Phase 1 provider dispatch:
    - route video-related generation through provider abstraction
    - reserve mock/kling/jimeng provider entrypoints for future integration

    Phase 1 session/history:
    - keep minimal in-memory session store
    - return session memory summary in response

    Phase 1 render package:
    - export a structured delivery package for downstream rendering/editing/publishing

    Phase 1 kling scene package:
    - export a manual scene-level package for Kling web generation

    Phase 2 minimal product closure:
    - generate image assets for each scene
    - synthesize final playable mp4 using images + audio + subtitles
    """

    def __init__(self) -> None:
        self._handlers = {
            "story": self._run_story,
            "storyboard": self._run_storyboard,
            "sentence_shots": self._run_sentence_shots,
            "image_prompts": self._run_image_prompts,
            "image_assets": self._run_image_assets,
            "video_prompts": self._run_video_prompts,
            "dialogue_script": self._run_dialogue_script,
            "audio_segments": self._run_audio_segments,
            "narration": self._run_narration,
            "subtitles": self._run_subtitles,
            "render_plan": self._run_render_plan,
            "final_video": self._run_final_video,
        }
        self._session_store: Dict[str, Dict[str, Any]] = {}

    def get_real_kling_samples_manifest(self) -> Dict[str, Any]:
        manifest = self._build_real_samples_manifest()
        samples = manifest.get("samples") or []

        available_scene_ids = [
            str(sample.get("scene_id")) for sample in samples if sample.get("scene_id")
        ]

        latest_sample_id = None
        if samples:
            latest_sample_id = samples[-1].get("sample_id")

        return {
            **manifest,
            "sample_count": len(samples),
            "latest_sample_id": latest_sample_id,
            "available_scene_ids": available_scene_ids,
        }

    def get_samples_summary(self) -> Dict[str, Any]:
        kling_manifest = self.get_real_kling_samples_manifest()

        provider_stats = {
            "kling": {
                "sample_count": kling_manifest.get("sample_count", 0),
                "latest_sample_id": kling_manifest.get("latest_sample_id"),
                "available_scene_ids": kling_manifest.get("available_scene_ids", []),
            }
        }

        providers = [
            provider
            for provider, stats in provider_stats.items()
            if stats.get("sample_count", 0) > 0
        ]

        total_sample_count = sum(
            int(stats.get("sample_count", 0)) for stats in provider_stats.values()
        )

        return {
            "providers": providers,
            "total_sample_count": total_sample_count,
            "provider_stats": provider_stats,
        }

    def get_real_kling_sample_by_id(self, sample_id: str) -> Optional[Dict[str, Any]]:
        manifest = self.get_real_kling_samples_manifest()
        samples = manifest.get("samples") or []

        for sample in samples:
            if str(sample.get("sample_id")) == sample_id:
                return sample

        return None

    def _env_bool(self, name: str, default: bool) -> bool:
        value = os.getenv(name, "").strip().lower()
        if not value:
            return default
        return value in {"1", "true", "yes", "y", "on"}

    def _env_float(self, name: str, default: float) -> float:
        value = os.getenv(name, "").strip()
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _tts_enabled(self) -> bool:
        return self._env_bool("TTS_ENABLED", False)

    def _tts_fallback_to_mock(self) -> bool:
        return self._env_bool("TTS_FALLBACK_TO_MOCK", True)

    def _tts_provider_name(self) -> str:
        provider = os.getenv("TTS_PROVIDER", DEFAULT_TTS_PROVIDER).strip()
        return provider or DEFAULT_TTS_PROVIDER

    def _tts_api_base_url(self) -> str:
        value = os.getenv("TTS_API_BASE_URL", DEFAULT_TTS_API_BASE_URL).strip()
        return value.rstrip("/") or DEFAULT_TTS_API_BASE_URL

    def _tts_api_key(self) -> str:
        tts_key = os.getenv("TTS_API_KEY", "").strip()
        if tts_key:
            return tts_key
        return os.getenv("OPENAI_API_KEY", "").strip()

    def _tts_model(self) -> str:
        value = os.getenv("TTS_MODEL", "").strip()
        if value:
            return value
        raise RuntimeError("TTS_MODEL is missing")

    def _tts_timeout_seconds(self) -> float:
        return self._env_float("TTS_TIMEOUT_SECONDS", 120.0)

    def _tts_voice_for(self, speaker: str, voice_style: str) -> str:
        speaker_key = speaker.strip().upper()
        speaker_specific = os.getenv(f"TTS_VOICE_{speaker_key}", "").strip()
        if speaker_specific:
            return speaker_specific

        style_key = voice_style.strip().upper()
        style_specific = os.getenv(f"TTS_VOICE_STYLE_{style_key}", "").strip()
        if style_specific:
            return style_specific

        default_voice = os.getenv("TTS_VOICE", "").strip()
        if default_voice:
            return default_voice

        raise RuntimeError("TTS_VOICE is missing")

    def _ensure_audio_run_dir(self, run_id: str) -> Path:
        run_dir = MOCK_AUDIO_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _ensure_image_run_dir(self, run_id: str) -> Path:
        run_dir = MOCK_IMAGE_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _probe_audio_duration_seconds(self, audio_path: Path) -> Optional[float]:
        if not audio_path.exists():
            return None

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception:
            return None

        raw_value = (result.stdout or "").strip()
        if not raw_value:
            return None

        try:
            duration = float(raw_value)
        except ValueError:
            return None

        if duration <= 0:
            return None

        return round(duration, 3)
    def _ensure_video_run_dir(self, run_id: str) -> Path:
        run_dir = MOCK_VIDEO_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _write_audio_directory_manifest(
        self, run_id: str, assets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        run_dir = self._ensure_audio_run_dir(run_id)
        asset_files: List[Dict[str, Any]] = []

        for asset in assets:
            file_name = str(asset.get("file_name", "unknown.mp3"))
            metadata_name = f"{file_name}.json"
            metadata_path = run_dir / metadata_name

            metadata_payload = {
                "asset_id": asset.get("asset_id"),
                "segment_id": asset.get("segment_id"),
                "scene_id": asset.get("scene_id"),
                "speaker": asset.get("speaker"),
                "voice_style": asset.get("voice_style"),
                "file_name": file_name,
                "public_url": asset.get("public_url"),
                "mime_type": asset.get("mime_type"),
                "duration_estimate_sec": asset.get("duration_estimate_sec"),
                "asset_status": asset.get("asset_status"),
                "generation_mode": asset.get("generation_mode"),
                "waveform_preview": asset.get("waveform_preview", []),
                "metadata": asset.get("metadata", {}),
            }

            metadata_path.write_text(
                json.dumps(metadata_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            asset_files.append(
                {
                    "asset_id": asset.get("asset_id"),
                    "file_name": file_name,
                    "audio_public_url": asset.get("public_url"),
                    "metadata_file": metadata_name,
                    "metadata_public_url": f"/assets/mock/audio/{run_id}/{metadata_name}",
                }
            )

        index_payload = {
            "manifest_type": "audio_directory_index",
            "run_id": run_id,
            "asset_count": len(assets),
            "run_directory": f"assets/mock/audio/{run_id}",
            "public_base_url": f"/assets/mock/audio/{run_id}",
            "assets": asset_files,
        }

        index_path = run_dir / "index.json"
        index_path.write_text(
            json.dumps(index_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "run_directory": f"assets/mock/audio/{run_id}",
            "public_base_url": f"/assets/mock/audio/{run_id}",
            "index_file": "index.json",
            "index_public_url": f"/assets/mock/audio/{run_id}/index.json",
            "asset_files": asset_files,
        }

    def _group_audio_assets_by_scene(
        self, assets: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}

        for asset in assets:
            scene_id = str(asset.get("scene_id") or "unknown_scene")
            grouped.setdefault(scene_id, []).append(
                {
                    "asset_id": asset.get("asset_id"),
                    "segment_id": asset.get("segment_id"),
                    "speaker": asset.get("speaker"),
                    "file_name": asset.get("file_name"),
                    "public_url": asset.get("public_url"),
                    "duration_estimate_sec": asset.get("duration_estimate_sec"),
                }
            )

        return [
            {
                "scene_id": scene_id,
                "assets": grouped[scene_id],
            }
            for scene_id in sorted(grouped.keys())
        ]

    def _generate_real_tts_audio(
        self,
        *,
        text: str,
        speaker: str,
        voice_style: str,
        output_path: Path,
    ) -> Dict[str, Any]:
        import http.client
        import ssl
        import time

        api_key = self._tts_api_key()
        if not api_key:
            raise RuntimeError("TTS_API_KEY is missing")

        model = self._tts_model()
        voice = self._tts_voice_for(speaker, voice_style)
        payload = {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": "mp3",
        }

        req = urllib_request.Request(
            url=f"{self._tts_api_base_url()}/audio/speech",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        attempts = 3
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                with urllib_request.urlopen(
                    req, timeout=self._tts_timeout_seconds()
                ) as resp:
                    data = resp.read()

                if not data:
                    raise RuntimeError("TTS response is empty")

                output_path.write_bytes(data)

                return {
                    "provider": self._tts_provider_name(),
                    "model": model,
                    "voice": voice,
                    "output_bytes": len(data),
                }

            except urllib_error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")

                # 4xx 基本属于请求本身有问题，不做重试，直接抛
                if 400 <= e.code < 500:
                    raise RuntimeError(
                        f"TTS http error: status={e.code}, detail={detail}"
                    ) from e

                last_error = RuntimeError(
                    f"TTS http error: status={e.code}, detail={detail}"
                )

            except http.client.IncompleteRead as e:
                last_error = RuntimeError(
                    f"TTS incomplete read: partial_bytes={len(e.partial or b'')}"
                )

            except urllib_error.URLError as e:
                last_error = RuntimeError(f"TTS request failed: {e.reason}")

            except ssl.SSLError as e:
                last_error = RuntimeError(f"TTS ssl error: {e}")

            except TimeoutError as e:
                last_error = RuntimeError(f"TTS timeout: {e}")

            if attempt < attempts:
                time.sleep(attempt)

        raise RuntimeError(str(last_error) if last_error else "TTS request failed")

    def run(self, req: WorkflowRunRequest) -> WorkflowRunResponse:
        run_id = f"run_{uuid4().hex[:12]}"
        ctx = StepContext(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=run_id,
            input=req.input,
        )

        previous_session_data = self._get_session_data(req.session_id)

        step_results: List[StepResult] = []
        aggregated_outputs: Dict[str, Any] = {}

        for step in req.steps:
            name = step.name.strip()
            handler = self._handlers.get(name)
            if handler is None:
                raise UnknownStepError(f"Unknown step: {name}")

            output = handler(ctx, aggregated_outputs)
            step_results.append(
                StepResult(name=name, status="COMPLETED", output=output)
            )
            aggregated_outputs[name] = output

        session_memory_summary = self._build_session_memory_summary(
            req.session_id,
            previous_session_data,
            aggregated_outputs,
        )
        self._save_session_data(req, aggregated_outputs)
        render_package = self._build_render_package(ctx, aggregated_outputs)

        character_candidates = self._build_character_candidates(req.input)
        character_manifest = self._build_character_manifest(req.input, character_candidates)

        aggregated_outputs["character_candidates"] = {
            "enabled": bool(req.input.structured_characters_enabled),
            "count": len(character_candidates),
            "items": character_candidates,
        }
        aggregated_outputs["character_manifest"] = {
            "enabled": bool(req.input.structured_characters_enabled),
            "count": len(character_manifest),
            "characters": character_manifest,
        }

        return WorkflowRunResponse(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=run_id,
            status="COMPLETED",
            steps=step_results,
            outputs=aggregated_outputs,
            session_memory_summary=session_memory_summary,
            render_package=render_package,
            timestamp=WorkflowRunResponse.now_timestamp(),
        )
    
    def _build_character_candidates(self, workflow_input: WorkflowInput) -> List[Dict[str, Any]]:
        if workflow_input.structured_characters_enabled and workflow_input.characters:
            items: List[Dict[str, Any]] = []
            for index, character in enumerate(workflow_input.characters, start=1):
                items.append(
                    {
                        "candidate_id": f"candidate_{index:02d}",
                        "display_name": character.display_name.strip(),
                        "species": character.species.strip(),
                        "role_type": character.role_type,
                        "visual_traits": character.visual_traits.strip(),
                        "forbidden_traits": character.forbidden_traits.strip(),
                        "source": "structured_input",
                    }
                )
            return items

        items: List[Dict[str, Any]] = []

        main_display_name = (
            workflow_input.main_character_display.strip()
            or workflow_input.main_character.strip()
        )
        if main_display_name:
            items.append(
                {
                    "candidate_id": "candidate_01",
                    "display_name": main_display_name,
                    "species": workflow_input.main_character_species.strip() or "rabbit",
                    "role_type": "primary",
                    "visual_traits": workflow_input.main_character_visual_traits.strip(),
                    "forbidden_traits": "",
                    "source": "legacy_main_character",
                }
            )

        secondary_display_name = (
            workflow_input.secondary_character_display.strip()
            or workflow_input.secondary_character.strip()
        )
        if secondary_display_name:
            items.append(
                {
                    "candidate_id": f"candidate_{len(items) + 1:02d}",
                    "display_name": secondary_display_name,
                    "species": workflow_input.secondary_character_species.strip() or "turtle",
                    "role_type": "secondary",
                    "visual_traits": workflow_input.secondary_character_visual_traits.strip(),
                    "forbidden_traits": "",
                    "source": "legacy_secondary_character",
                }
            )

        return items


    def _build_character_manifest(
        self,
        workflow_input: WorkflowInput,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        manifest: List[Dict[str, Any]] = []

        for candidate in candidates:
            role_type = str(candidate.get("role_type") or "secondary").strip()
            if role_type == "primary":
                character_id = "char_primary_01"
            else:
                secondary_index = (
                    sum(
                        1
                        for item in manifest
                        if str(item.get("role_type") or "").strip() == "secondary"
                    )
                    + 1
                )
                character_id = f"char_secondary_{secondary_index:02d}"

            visual_traits_text = str(candidate.get("visual_traits") or "").strip()
            forbidden_traits_text = str(candidate.get("forbidden_traits") or "").strip()

            signature_traits = [
                item.strip()
                for item in visual_traits_text.split(",")
                if item.strip()
            ]
            forbidden_traits = [
                item.strip()
                for item in forbidden_traits_text.split(",")
                if item.strip()
            ]

            manifest.append(
                {
                    "character_id": character_id,
                    "display_name": str(candidate.get("display_name") or "").strip(),
                    "species": str(candidate.get("species") or "").strip(),
                    "role_type": role_type,
                    "signature_traits": signature_traits,
                    "forbidden_traits": forbidden_traits,
                    "locking_level": "strict",
                    "reference_assets": {
                        "status": "pending",
                        "front_view": None,
                        "side_view": None,
                        "three_quarter_view": None,
                    },
                    "source": str(candidate.get("source") or "").strip(),
                }
            )

        return manifest
    def _build_character_manifest(
        self,
        workflow_input: WorkflowInput,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        manifest: List[Dict[str, Any]] = []

        for index, candidate in enumerate(candidates, start=1):
            role_type = str(candidate.get("role_type") or "secondary").strip()
            if role_type == "primary":
                character_id = "char_primary_01"
            else:
                secondary_index = sum(
                    1
                    for item in manifest
                    if str(item.get("role_type") or "").strip() == "secondary"
                ) + 1
                character_id = f"char_secondary_{secondary_index:02d}"

            visual_traits_text = str(candidate.get("visual_traits") or "").strip()
            forbidden_traits_text = str(candidate.get("forbidden_traits") or "").strip()

            signature_traits = [
                item.strip()
                for item in visual_traits_text.split(",")
                if item.strip()
            ]
            forbidden_traits = [
                item.strip()
                for item in forbidden_traits_text.split(",")
                if item.strip()
            ]

            manifest.append(
                {
                    "character_id": character_id,
                    "display_name": str(candidate.get("display_name") or "").strip(),
                    "species": str(candidate.get("species") or "").strip(),
                    "role_type": role_type,
                    "signature_traits": signature_traits,
                    "forbidden_traits": forbidden_traits,
                    "locking_level": "strict",
                    "reference_assets": {
                        "status": "pending",
                        "front_view": None,
                        "side_view": None,
                        "three_quarter_view": None,
                    },
                    "source": str(candidate.get("source") or "").strip(),
                }
            )

        return manifest

    def _get_session_data(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        return self._session_store.get(session_id)

    def _save_session_data(
        self, req: WorkflowRunRequest, outputs: Dict[str, Any]
    ) -> None:
        if not req.session_id:
            return

        self._session_store[req.session_id] = {
            "workflow_id": req.workflow_id,
            "last_input": req.input.model_dump(),
            "last_story": outputs.get("story") or {},
            "last_storyboard": outputs.get("storyboard") or {},
            "last_render_plan": outputs.get("render_plan") or {},
        }

    def _build_session_memory_summary(
        self,
        session_id: Optional[str],
        previous_session_data: Optional[Dict[str, Any]],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not session_id:
            return {
                "enabled": False,
                "session_id": None,
                "has_previous_session": False,
            }

        current_story = outputs.get("story") or {}
        current_storyboard = outputs.get("storyboard") or {}

        summary: Dict[str, Any] = {
            "enabled": True,
            "session_id": session_id,
            "has_previous_session": previous_session_data is not None,
            "current_story_title": current_story.get("title"),
            "current_scene_count": current_storyboard.get("scene_count"),
        }

        if previous_session_data is not None:
            last_input = previous_session_data.get("last_input") or {}
            last_story = previous_session_data.get("last_story") or {}
            last_storyboard = previous_session_data.get("last_storyboard") or {}
            summary["previous_topic"] = last_input.get("topic")
            summary["previous_story_title"] = last_story.get("title")
            summary["previous_scene_count"] = last_storyboard.get("scene_count")

        return summary

    def _scene_count(self, duration_sec: int) -> int:
        if duration_sec <= 30:
            return 3
        if duration_sec <= 60:
            return 4
        if duration_sec <= 90:
            return 5
        return 6

    def _audience_label(self, audience: str) -> str:
        mapping = {
            "children": "小朋友",
            "kids": "小朋友",
            "general": "所有人",
            "family": "亲子家庭",
            "teen": "青少年",
        }
        return mapping.get(audience.lower(), audience)

    def _tone_label(self, tone: str) -> str:
        mapping = {
            "warm": "温暖",
            "funny": "轻松有趣",
            "healing": "治愈",
            "adventure": "冒险",
            "gentle": "柔和",
        }
        return mapping.get(tone.lower(), tone)

    def _visual_style_label(self, visual_style: str) -> str:
        mapping = {
            "storybook": "绘本",
            "illustration": "插画",
            "cartoon": "卡通",
            "animation": "动画",
        }
        return mapping.get(visual_style.lower(), visual_style)

    def _character_style_label(self, character_style: str) -> str:
        mapping = {
            "animal": "小动物",
            "human": "人物",
            "fantasy": "奇幻角色",
        }
        return mapping.get(character_style.lower(), character_style)

    def _image_provider_name(self) -> str:
        provider = os.getenv("IMAGE_PROVIDER", DEFAULT_IMAGE_PROVIDER).strip()
        return provider or DEFAULT_IMAGE_PROVIDER

    def _image_fallback_provider_name(self) -> str:
        provider = os.getenv(
            "IMAGE_FALLBACK_PROVIDER", DEFAULT_IMAGE_FALLBACK_PROVIDER
        ).strip()
        return provider or DEFAULT_IMAGE_FALLBACK_PROVIDER

    def _api_image_enabled(self) -> bool:
        value = os.getenv("API_IMAGE_ENABLED", "false").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _api_image_fallback_to_pillow(self) -> bool:
        value = os.getenv("KLING_IMAGE_FALLBACK_TO_PILLOW", "true").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _normalized_video_provider(self, provider: str) -> str:
        value = provider.strip().lower()
        if not value:
            return "mock"
        return value

    def _normalized_voice_mode(self, voice_mode: str) -> str:
        value = voice_mode.strip().lower()
        if value in {"single", "multi", "character"}:
            return value
        return "single"

    def _speaker_profiles(self, ctx: StepContext) -> Dict[str, str]:
        profiles = dict(ctx.input.speaker_profiles or {})
        return {
            "narrator": profiles.get("narrator", ctx.input.voice_style),
            "mother": profiles.get("mother", "warm_female"),
            "child": profiles.get("child", "gentle_child"),
        }

    def _character_speaker_profiles(self, ctx: StepContext) -> Dict[str, str]:
        profiles = dict(getattr(ctx.input, "character_speaker_profiles", {}) or {})
        return {
            "narrator": profiles.get("narrator", ctx.input.voice_style),
            "main_character": profiles.get("main_character", "gentle_child"),
            "secondary_character": profiles.get("secondary_character", "warm_male"),
        }

    def _character_speaker_name(self, ctx: StepContext) -> str:
        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_character:
            normalized = main_character.lower().replace(" ", "_")
            return normalized
        return "main_character"
    
    def _secondary_character_speaker_name(self, ctx: StepContext) -> str:
        secondary_character = str(
            getattr(ctx.input, "secondary_character", "") or ""
        ).strip()
        if secondary_character:
            normalized = secondary_character.lower().replace(" ", "_")
            return normalized
        return "secondary_character"

    def _detect_character_speaker(self, ctx: StepContext, text: str) -> str:
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
            return "narrator"

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
    
    def _resolve_character_speaker(
        self, ctx: StepContext, text: str
    ) -> Dict[str, str]:
        character_profiles = self._character_speaker_profiles(ctx)
        main_character_speaker = self._character_speaker_name(ctx)
        secondary_character_speaker = self._secondary_character_speaker_name(ctx)

        detected_role = self._detect_character_speaker(ctx, text)

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

    def _build_dialogue_line(
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
    def _main_character_display_label(self, ctx: StepContext) -> str:
        display_value = str(
            getattr(ctx.input, "main_character_display", "") or ""
        ).strip()
        if display_value:
            return display_value

        main_value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_value:
            return main_value

        return self._character_style_label(ctx.input.character_style)

    def _main_character_display_label(self, ctx: StepContext) -> str:
        display_value = str(
            getattr(ctx.input, "main_character_display", "") or ""
        ).strip()
        if display_value:
            return display_value

        main_value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_value:
            return main_value

        return self._character_style_label(ctx.input.character_style)
    def _secondary_character_display_label(self, ctx: StepContext) -> str:
        display_value = str(
            getattr(ctx.input, "secondary_character_display", "") or ""
        ).strip()
        if display_value:
            return display_value

        secondary_value = str(getattr(ctx.input, "secondary_character", "") or "").strip()
        if secondary_value:
            return secondary_value

        return ""

    def _has_secondary_character(self, ctx: StepContext) -> bool:
        return bool(self._secondary_character_display_label(ctx))
    def _main_character_label(self, ctx: StepContext) -> str:
        value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if value:
            return value
        return self._character_style_label(ctx.input.character_style)

    def _main_character_subject(self, ctx: StepContext) -> str:
        value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if value:
            return value
        return f"{ctx.input.character_style} protagonist"

    def _character_consistency_anchor(self, ctx: StepContext) -> str:
        explicit_anchor = str(
            getattr(ctx.input, "character_consistency_anchor", "") or ""
        ).strip()
        if explicit_anchor:
            return explicit_anchor

        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_character:
            return (
                f"{main_character}, "
                "same character across all scenes, "
                "consistent facial features, "
                "consistent body shape, "
                "consistent outfit and visual identity, "
                "cute expressive face, "
                "storybook details"
            )

        return (
            f"{ctx.input.character_style} protagonist, "
            "same character across all scenes, "
            "consistent facial features, "
            "consistent body shape, "
            "consistent outfit and visual identity, "
            "cute expressive face, "
            "storybook details"
        )

    def _character_prompt_phrase(self, ctx: StepContext) -> str:
        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_character:
            return main_character
        return f"{ctx.input.character_style} protagonist"
    
    def _build_story_paragraphs(self, ctx: StepContext) -> List[str]:
        topic = ctx.input.topic.strip() or "一个温暖的童话故事"
        audience_label = self._audience_label(ctx.input.audience)
        tone_label = self._tone_label(ctx.input.tone)
        visual_label = self._visual_style_label(ctx.input.visual_style)
        main_character_display = self._main_character_display_label(ctx)
        secondary_character_display = self._secondary_character_display_label(ctx)
        has_secondary_character = self._has_secondary_character(ctx)

        if has_secondary_character:
            paragraph_1 = (
                f"在一个安静又明亮的清晨，围绕“{topic}”展开了一段{tone_label}的小故事。"
                f"故事的主角是可爱的{main_character_display}，它和朋友{secondary_character_display}一起踏上了新的旅程。"
            )
            paragraph_2 = (
                f"起初，一切都很顺利，可没过多久，{main_character_display}遇到了一点小麻烦。"
                f"{secondary_character_display}陪在它身边，一起观察周围的变化，也一起思考接下来该怎么办。"
            )
            paragraph_3 = (
                f"在一路上的观察、尝试和彼此鼓励下，{main_character_display}慢慢鼓起勇气，"
                f"{secondary_character_display}也主动帮忙，它们一点点找到了解决问题的方法。"
            )
            paragraph_4 = (
                f"最后，{main_character_display}和{secondary_character_display}顺利完成了这段旅程，"
                f"也一起收获了陪伴、勇气和成长。"
                f"这是一个适合{audience_label}观看、适合用{visual_label}风格呈现的{tone_label}故事。"
            )
            return [paragraph_1, paragraph_2, paragraph_3, paragraph_4]

        paragraph_1 = (
            f"在一个安静又明亮的清晨，围绕“{topic}”展开了一段{tone_label}的小故事。"
            f"故事的主角是一位可爱的{main_character_display}，它带着好奇心走进了新的旅程。"
        )
        paragraph_2 = (
            f"起初，一切都很顺利，可没过多久，这位{main_character_display}就遇到了一点小麻烦。"
            f"它有些紧张，也有些犹豫，不知道该不该继续往前走。"
        )
        paragraph_3 = (
            f"但在一路上的观察、尝试和他人的帮助下，这位{main_character_display}慢慢鼓起勇气，"
            f"一点点找到了解决问题的方法，也学会了相信自己。"
        )
        paragraph_4 = (
            f"最后，这位{main_character_display}顺利完成了这段旅程，也收获了陪伴、勇气和成长。"
            f"这是一个适合{audience_label}观看、适合用{visual_label}风格呈现的{tone_label}故事。"
        )

        return [paragraph_1, paragraph_2, paragraph_3, paragraph_4]

    def _scene_blueprints(
        self, ctx: StepContext, scene_count: int
    ) -> List[Dict[str, str]]:
        tone_label = self._tone_label(ctx.input.tone)
        visual_label = self._visual_style_label(ctx.input.visual_style)
        main_character_display = self._main_character_display_label(ctx)

        base = [
            {
                "scene_title": "故事开场",
                "visual_description": (
                    f"{visual_label}风格画面，晨光柔和，主角{main_character_display}第一次出场，"
                    f"整体氛围{tone_label}、轻盈而有期待感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "遇到问题",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}停下脚步思考，"
                    f"周围环境出现小小变化，画面强调困惑与转折。"
                ),
                "shot_type": "medium",
                "transition": "cut",
            },
            {
                "scene_title": "行动推进",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}主动尝试解决问题，"
                    f"动作更明确，节奏变得积极，画面更有前进感。"
                ),
                "shot_type": "medium",
                "transition": "dissolve",
            },
            {
                "scene_title": "温暖收束",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}完成旅程，表情放松，"
                    f"画面回到温暖明亮的氛围，用来承接结尾情绪。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
            {
                "scene_title": "回味结尾",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}回头望向来时的路，"
                    f"环境安静舒展，用于强化余韵与成长感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "片尾定格",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}站在新的起点上，"
                    f"适合作为片尾定格镜头，氛围柔和完整。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
        ]
        return base[:scene_count]
    
    def _scene_blueprints(
        self, ctx: StepContext, scene_count: int
    ) -> List[Dict[str, str]]:
        tone_label = self._tone_label(ctx.input.tone)
        visual_label = self._visual_style_label(ctx.input.visual_style)
        main_character_display = self._main_character_display_label(ctx)
        secondary_character_display = self._secondary_character_display_label(ctx)
        has_secondary_character = self._has_secondary_character(ctx)

        if has_secondary_character:
            base = [
                {
                    "scene_title": "故事开场",
                    "visual_description": (
                        f"{visual_label}风格画面，晨光柔和，主角{main_character_display}和朋友{secondary_character_display}第一次一起出场，"
                        f"整体氛围{tone_label}、轻盈而有期待感。"
                    ),
                    "shot_type": "wide",
                    "transition": "fade",
                },
                {
                    "scene_title": "遇到问题",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}停下脚步思考，"
                        f"{secondary_character_display}陪在一旁一起观察环境变化，画面强调困惑与转折。"
                    ),
                    "shot_type": "medium",
                    "transition": "cut",
                },
                {
                    "scene_title": "行动推进",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}与{secondary_character_display}一起尝试解决问题，"
                        f"动作更明确，节奏变得积极，画面更有前进感。"
                    ),
                    "shot_type": "medium",
                    "transition": "dissolve",
                },
                {
                    "scene_title": "温暖收束",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}和{secondary_character_display}完成旅程，表情放松，"
                        f"画面回到温暖明亮的氛围，用来承接结尾情绪。"
                    ),
                    "shot_type": "close-up",
                    "transition": "fade",
                },
                {
                    "scene_title": "回味结尾",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}和{secondary_character_display}回头望向来时的路，"
                        f"环境安静舒展，用于强化余韵与成长感。"
                    ),
                    "shot_type": "wide",
                    "transition": "fade",
                },
                {
                    "scene_title": "片尾定格",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}和{secondary_character_display}站在新的起点上，"
                        f"适合作为片尾定格镜头，氛围柔和完整。"
                    ),
                    "shot_type": "close-up",
                    "transition": "fade",
                },
            ]
            return base[:scene_count]

        base = [
            {
                "scene_title": "故事开场",
                "visual_description": (
                    f"{visual_label}风格画面，晨光柔和，主角{main_character_display}第一次出场，"
                    f"整体氛围{tone_label}、轻盈而有期待感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "遇到问题",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}停下脚步思考，"
                    f"周围环境出现小小变化，画面强调困惑与转折。"
                ),
                "shot_type": "medium",
                "transition": "cut",
            },
            {
                "scene_title": "行动推进",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}主动尝试解决问题，"
                    f"动作更明确，节奏变得积极，画面更有前进感。"
                ),
                "shot_type": "medium",
                "transition": "dissolve",
            },
            {
                "scene_title": "温暖收束",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}完成旅程，表情放松，"
                    f"画面回到温暖明亮的氛围，用来承接结尾情绪。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
            {
                "scene_title": "回味结尾",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}回头望向来时的路，"
                    f"环境安静舒展，用于强化余韵与成长感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "片尾定格",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}站在新的起点上，"
                    f"适合作为片尾定格镜头，氛围柔和完整。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
        ]
        return base[:scene_count]

    def _build_video_provider_prompts(
        self, ctx: StepContext, scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        provider = self._normalized_video_provider(ctx.input.video_provider)

        if provider == "mock":
            return self._build_mock_video_prompts(ctx, scenes)
        if provider == "kling":
            return self._build_kling_video_prompts(ctx, scenes)
        if provider == "jimeng":
            return self._build_jimeng_video_prompts(ctx, scenes)

        raise UnknownVideoProviderError(f"Unknown video provider: {provider}")

    def _build_mock_video_prompts(
        self, ctx: StepContext, scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        prompts: List[Dict[str, Any]] = []
        character_phrase = self._character_prompt_phrase(ctx)

        for scene in scenes:
            base = self._build_video_prompt_base(ctx, scene)
            prompt = (
                f"Create a short animated video shot in {ctx.input.visual_style} style, "
                f"{ctx.input.tone} atmosphere, with {character_phrase}. "
                f"Scene description: {base['visual_description']}. "
                f"Narration context: {base['narration']}"
            )
            prompts.append(
                {
                    "scene_id": base["scene_id"],
                    "scene_title": base["scene_title"],
                    "provider": "mock",
                    "prompt": prompt,
                    "duration_sec": base["duration_sec"],
                    "shot_type": base["shot_type"],
                    "transition": base["transition"],
                }
            )

        return {
            "provider": "mock",
            "mode": "placeholder",
            "integration_status": "mock_only",
            "prompts": prompts,
        }

    def _build_kling_video_prompts(
        self, ctx: StepContext, scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        prompts: List[Dict[str, Any]] = []
        character_phrase = self._character_prompt_phrase(ctx)

        for scene in scenes:
            base = self._build_video_prompt_base(ctx, scene)
            prompts.append(
                {
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
            )

        return {
            "provider": "kling",
            "mode": "adapter_placeholder",
            "integration_status": "pending_api_integration",
            "prompts": prompts,
        }

    def _build_jimeng_video_prompts(
        self, ctx: StepContext, scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        prompts: List[Dict[str, Any]] = []
        character_phrase = self._character_prompt_phrase(ctx)

        for scene in scenes:
            base = self._build_video_prompt_base(ctx, scene)
            prompts.append(
                {
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
            )

        return {
            "provider": "jimeng",
            "mode": "adapter_placeholder",
            "integration_status": "pending_api_integration",
            "prompts": prompts,
        }

    def _build_render_plan_by_provider(
        self, ctx: StepContext, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        provider = self._normalized_video_provider(ctx.input.video_provider)

        if provider == "mock":
            return self._build_mock_render_plan(ctx, scenes, subtitles_enabled)
        if provider == "kling":
            return self._build_kling_render_plan(ctx, scenes, subtitles_enabled)
        if provider == "jimeng":
            return self._build_jimeng_render_plan(ctx, scenes, subtitles_enabled)

        raise UnknownVideoProviderError(f"Unknown video provider: {provider}")

    def _base_asset_plan(
        self, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> List[Dict[str, Any]]:
        asset_plan: List[Dict[str, Any]] = []
        for scene in scenes:
            asset_plan.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "image_required": True,
                    "video_required": True,
                    "audio_required": True,
                    "subtitle_required": subtitles_enabled,
                }
            )
        return asset_plan

    def _build_mock_render_plan(
        self, ctx: StepContext, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "output_mode": ctx.input.output_mode,
            "total_duration_sec": ctx.input.duration_sec,
            "scene_count": len(scenes),
            "asset_plan": self._base_asset_plan(scenes, subtitles_enabled),
            "edit_plan": {
                "subtitle_enabled": ctx.input.subtitle_enabled,
                "voice_style": ctx.input.voice_style,
                "visual_style": ctx.input.visual_style,
                "note": (
                    "Phase 1 render plan placeholder: "
                    "可继续对接可灵/即梦/剪映素材整合链路"
                ),
            },
        }

    def _build_kling_render_plan(
        self, ctx: StepContext, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        return {
            "provider": "kling",
            "output_mode": ctx.input.output_mode,
            "total_duration_sec": ctx.input.duration_sec,
            "scene_count": len(scenes),
            "asset_plan": self._base_asset_plan(scenes, subtitles_enabled),
            "edit_plan": {
                "subtitle_enabled": ctx.input.subtitle_enabled,
                "voice_style": ctx.input.voice_style,
                "visual_style": ctx.input.visual_style,
                "adapter_status": "pending_api_integration",
                "next_step": "connect kling video generation api",
            },
        }

    def _build_jimeng_render_plan(
        self, ctx: StepContext, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        return {
            "provider": "jimeng",
            "output_mode": ctx.input.output_mode,
            "total_duration_sec": ctx.input.duration_sec,
            "scene_count": len(scenes),
            "asset_plan": self._base_asset_plan(scenes, subtitles_enabled),
            "edit_plan": {
                "subtitle_enabled": ctx.input.subtitle_enabled,
                "voice_style": ctx.input.voice_style,
                "visual_style": ctx.input.visual_style,
                "adapter_status": "pending_api_integration",
                "next_step": "connect jimeng video generation api",
            },
        }

    def _build_real_samples_manifest(self) -> Dict[str, Any]:
        return {
            "provider": "kling",
            "manifest_type": "real_samples",
            "version": "v1",
            "samples": [
                {
                    "sample_id": "kling-scene-01-real-sample",
                    "scene_id": "scene-01",
                    "generated_scene_id": "scene_01",
                    "status": "archived",
                    "notes": (
                        "First real Kling scene sample archived for project "
                        "render-package backfill."
                    ),
                    "assets": {
                        "notes": "assets/samples/kling/scene-01/docs/scene-01-kling-notes.md",
                        "clean_video": "assets/samples/kling/scene-01/scene-01-kling-clean.mp4",
                        "watermarked_video": (
                            "assets/samples/kling/scene-01/scene-01-kling-watermarked.mp4"
                        ),
                        "input_screenshot": (
                            "assets/samples/kling/scene-01/screenshots/"
                            "scene-01-kling-input.png"
                        ),
                        "result_screenshots": [
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-01.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-02.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-03.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-04.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-05.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-06.png",
                        ],
                    },
                }
            ],
        }

    def _build_kling_scene_package(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        if not scenes:
            return {}

        scene = scenes[0]
        visual_description = str(scene.get("visual_description", ""))
        narration = str(scene.get("narration", ""))
        shot_type = str(scene.get("shot_type", "wide"))
        transition = str(scene.get("transition", "fade"))
        duration_sec = int(scene.get("duration_sec", 15))

        recommended_prompt = (
            f"{ctx.input.visual_style} style video, {ctx.input.tone} atmosphere, "
            f"{ctx.input.character_style} protagonist, {visual_description}, "
            f"camera shot: {shot_type}, transition feeling: {transition}, "
            f"story context: {narration}"
        )

        return {
            "provider": "kling",
            "scene_id": scene.get("scene_id"),
            "scene_title": scene.get("scene_title"),
            "narration": narration,
            "visual_description": visual_description,
            "recommended_prompt": recommended_prompt,
            "recommended_duration_sec": duration_sec,
            "recommended_aspect_ratio": "9:16",
            "recommended_style": ctx.input.visual_style,
            "recommended_negative_prompt": (
                "low quality, blurry, distorted anatomy, broken composition, "
                "extra limbs, duplicated subject, unreadable details"
            ),
            "manual_generation_notes": [
                "打开可灵网页视频生成入口",
                "使用 recommended_prompt 作为主提示词",
                "时长优先使用 recommended_duration_sec",
                "画幅优先选择 9:16，适合短视频发布",
                "生成后将视频片段回填到项目四样例链中",
            ],
            "real_sample_manifest_ref": {
                "path": "assets/samples/kling/real_samples_manifest.json",
                "provider": "kling",
                "sample_id": "kling-scene-01-real-sample",
                "scene_id": "scene-01",
                "generated_scene_id": "scene_01",
            },
        }

    def _build_render_package(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        story = outputs.get("story") or {}
        storyboard = outputs.get("storyboard") or {}
        image_prompts = outputs.get("image_prompts") or {}
        image_assets = outputs.get("image_assets") or {}
        video_prompts = outputs.get("video_prompts") or {}
        dialogue_script = outputs.get("dialogue_script") or {}
        audio_segments = outputs.get("audio_segments") or {}
        narration = outputs.get("narration") or {}
        subtitles = outputs.get("subtitles") or {}
        render_plan = outputs.get("render_plan") or {}
        final_video = outputs.get("final_video") or {}

        real_samples_manifest = self._build_real_samples_manifest()

        publish_manifest = {
            "topic": ctx.input.topic,
            "session_id": ctx.session_id,
            "video_provider": self._normalized_video_provider(ctx.input.video_provider),
            "output_mode": ctx.input.output_mode,
            "language": ctx.input.language,
            "voice_style": ctx.input.voice_style,
            "subtitle_enabled": ctx.input.subtitle_enabled,
            "scene_count": storyboard.get("scene_count"),
            "story_title": story.get("title"),
            "real_sample_manifest_ref": {
                "path": "assets/samples/kling/real_samples_manifest.json",
                "provider": "kling",
                "sample_count": len(real_samples_manifest.get("samples") or []),
            },
        }

        kling_scene_package = self._build_kling_scene_package(ctx, outputs)
        audio_assets_manifest = audio_segments.get("asset_manifest") or {
            "run_id": ctx.run_id,
            "provider": "mock_tts",
            "asset_count": 0,
            "assets": [],
        }
        audio_directory_manifest = audio_segments.get("directory_manifest") or {
            "run_directory": f"assets/mock/audio/{ctx.run_id}",
            "public_base_url": f"/assets/mock/audio/{ctx.run_id}",
            "index_file": "index.json",
            "index_public_url": f"/assets/mock/audio/{ctx.run_id}/index.json",
            "asset_files": [],
        }

        return {
            "format": "render_package_v1",
            "package_name": f"{ctx.workflow_id}_{ctx.run_id}",
            "files": {
                "story.json": story,
                "storyboard.json": storyboard,
                "image_prompts.json": image_prompts,
                "image_assets.json": image_assets,
                "video_prompts.json": video_prompts,
                "dialogue_script.json": dialogue_script,
                "audio_segments.json": audio_segments,
                "audio_directory_manifest.json": audio_directory_manifest,
                "audio_assets_manifest.json": audio_assets_manifest,
                "narration.txt": narration.get("full_text", ""),
                "subtitles.srt": subtitles.get("srt_preview", ""),
                "render_plan.json": render_plan,
                "final_video.json": final_video,
                "publish_manifest.json": publish_manifest,
                "kling_scene_package.json": kling_scene_package,
                "real_samples_manifest.json": real_samples_manifest,
            },
        }

    def _run_story(self, ctx: StepContext, outputs: Dict[str, Any]) -> Dict[str, Any]:
        topic = ctx.input.topic.strip() or "一个温暖的童话故事"
        paragraphs = self._build_story_paragraphs(ctx)
        title = f"{topic}的故事"
        summary = (
            f"一个围绕“{topic}”展开的短篇故事，整体气质温暖，"
            f"适合做成儿童向的多模态视频内容。"
        )
        text = "\n".join(paragraphs)

        return {
            "title": title,
            "summary": summary,
            "text": text,
            "style_profile": {
                "audience": ctx.input.audience,
                "tone": ctx.input.tone,
                "visual_style": ctx.input.visual_style,
                "character_style": ctx.input.character_style,
                "main_character": ctx.input.main_character,
                "main_character_display": ctx.input.main_character_display,
                "secondary_character": ctx.input.secondary_character,
                "secondary_character_display": ctx.input.secondary_character_display,
                "character_consistency_anchor": ctx.input.character_consistency_anchor,
                "language": ctx.input.language,
            },
        }

    def _run_storyboard(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        story = outputs.get("story") or {}
        story_text = str(story.get("text", ""))
        story_parts = [part.strip() for part in story_text.split("\n") if part.strip()]
        scene_count = self._scene_count(ctx.input.duration_sec)
        duration_per_scene = max(5, ctx.input.duration_sec // scene_count)

        while len(story_parts) < scene_count and story_parts:
            story_parts.append(story_parts[-1])

        if not story_parts:
            story_parts = ["一个温暖的故事正在展开。"] * scene_count

        story_parts = story_parts[:scene_count]
        blueprints = self._scene_blueprints(ctx, scene_count)

        scenes: List[Dict[str, Any]] = []
        for index, (segment, blueprint) in enumerate(
            zip(story_parts, blueprints), start=1
        ):
            scenes.append(
                {
                    "scene_id": f"scene_{index:02d}",
                    "scene_title": blueprint["scene_title"],
                    "visual_description": blueprint["visual_description"],
                    "narration": segment,
                    "duration_sec": duration_per_scene,
                    "shot_type": blueprint["shot_type"],
                    "transition": blueprint["transition"],
                }
            )

        return {
            "scene_count": len(scenes),
            "total_duration_sec": ctx.input.duration_sec,
            "scenes": scenes,
        }
    def _run_sentence_shots(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        items: List[Dict[str, Any]] = []
        shot_index = 1

        for scene in scenes:
            scene_id = str(scene.get("scene_id") or "").strip()
            scene_title = str(scene.get("scene_title") or "").strip()
            visual_description = str(scene.get("visual_description") or "").strip()
            narration = str(scene.get("narration") or "").strip()
            shot_type = str(scene.get("shot_type") or "medium").strip()
            transition = str(scene.get("transition") or "fade").strip()

            sentence_list = self._split_story_sentences(narration)
            if not sentence_list and narration:
                sentence_list = [narration]

            for sentence in sentence_list:
                shot_id = f"shot_{shot_index:02d}"
                items.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "visual_description": visual_description,
                        "shot_type": shot_type,
                        "transition": transition,
                        "text": sentence,
                        "subtitle_text": sentence,
                        "audio_text": sentence,
                    }
                )
                shot_index += 1

        return {
            "enabled": True,
            "shot_count": len(items),
            "items": items,
        }
    def _split_story_sentences(self, text: str) -> List[str]:
        normalized = str(text or "").replace("\n", " ").strip()
        if not normalized:
            return []

        sentences: List[str] = []
        current: List[str] = []
        hard_break_chars = {"。", "！", "？", "；", "!", "?", ";"}

        for ch in normalized:
            current.append(ch)
            if ch in hard_break_chars:
                sentence = "".join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []

        tail = "".join(current).strip()
        if tail:
            sentences.append(tail)

        merged: List[str] = []
        for sentence in sentences:
            compact = " ".join(sentence.split()).strip()
            if not compact:
                continue

            if merged and len(compact) < 8:
                merged[-1] = f"{merged[-1]}{compact}"
            else:
                merged.append(compact)

        if not merged and normalized:
            merged = [normalized]

        return merged[:10]

    def _run_image_prompts(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        global_style_anchor = (
            f"{ctx.input.visual_style} illustration, "
            f"{ctx.input.tone} mood, "
            "children's storybook art, "
            "soft pastel palette, "
            "warm gentle lighting, "
            "clean composition, "
            "consistent character design, "
            "vertical 9:16 framing"
        )

        character_anchor = self._character_consistency_anchor(ctx)

        prompts: List[Dict[str, Any]] = []

        if shot_items:
            for shot in shot_items:
                shot_id = str(shot.get("shot_id") or "").strip()
                scene_id = str(shot.get("scene_id") or "").strip()
                scene_title = str(shot.get("scene_title") or "").strip()
                visual_description = str(shot.get("visual_description") or "").strip()
                shot_type = str(shot.get("shot_type") or "medium").strip()
                transition = str(shot.get("transition") or "fade").strip()
                text = str(shot.get("text") or "").strip()

                shot_anchor = (
                    f"scene title: {scene_title}, "
                    f"camera shot: {shot_type}, "
                    f"transition feeling: {transition}, "
                    f"visual focus: {visual_description}"
                )

                story_anchor = f"story context: {text}"

                prompt = ", ".join(
                    part
                    for part in [
                        global_style_anchor,
                        character_anchor,
                        shot_anchor,
                        story_anchor,
                    ]
                    if part
                )

                prompts.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "prompt": prompt,
                    }
                )

            return {"provider": "image_prompt_builder", "prompts": prompts}

        for scene in scenes:
            scene_id = str(scene.get("scene_id") or "")
            narration = str(scene.get("narration", "")).strip()
            visual_description = str(scene.get("visual_description", "")).strip()
            shot_type = str(scene.get("shot_type", "medium")).strip()
            transition = str(scene.get("transition", "fade")).strip()
            scene_title = str(scene.get("scene_title", "")).strip()

            scene_anchor = (
                f"scene title: {scene_title}, "
                f"camera shot: {shot_type}, "
                f"transition feeling: {transition}, "
                f"visual focus: {visual_description}"
            )

            story_anchor = f"story context: {narration}"

            prompt = ", ".join(
                part
                for part in [
                    global_style_anchor,
                    character_anchor,
                    scene_anchor,
                    story_anchor,
                ]
                if part
            )

            prompts.append(
                {
                    "scene_id": scene_id,
                    "prompt": prompt,
                }
            )

        return {"provider": "image_prompt_builder", "prompts": prompts}
    def _build_scene_ppm(
        self, ctx: StepContext, scene: Dict[str, Any], index: int
    ) -> bytes:
        import io
        import math
        import textwrap
        from pathlib import Path

        width = 1280
        height = 720

        topic = str(getattr(ctx.input, "topic", "") or "Warm Story").strip()
        scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
        scene_title = str(scene.get("scene_title") or f"Scene {index}").strip()
        visual_description = str(scene.get("visual_description", "")).strip()
        narration = str(scene.get("narration", "")).strip()
        duration_sec = int(scene.get("duration_sec") or 0)

        body_text = narration or visual_description or "A warm and gentle story scene."
        body_text = body_text.replace("\n", " ").strip()

        themes = [
            {
                "sky_top": (109, 101, 255),
                "sky_bottom": (243, 236, 255),
                "ground": (236, 226, 220),
                "accent": (120, 104, 255),
                "accent_soft": (224, 218, 255),
                "text_primary": (45, 39, 84),
                "text_secondary": (97, 91, 130),
                "moon": (255, 246, 196),
                "star": (255, 255, 240),
                "cloud": (255, 255, 255),
                "hill": (211, 234, 221),
                "path": (245, 233, 210),
                "bush": (168, 214, 182),
                "shape_a": (255, 210, 218),
                "shape_b": (196, 229, 255),
                "shape_c": (216, 242, 220),
                "rabbit_body": (255, 251, 248),
                "rabbit_ear": (255, 216, 224),
                "rabbit_cloth": (243, 184, 118),
            },
            {
                "sky_top": (255, 188, 134),
                "sky_bottom": (255, 241, 227),
                "ground": (244, 232, 220),
                "accent": (244, 134, 92),
                "accent_soft": (255, 220, 204),
                "text_primary": (94, 57, 38),
                "text_secondary": (138, 99, 80),
                "moon": (255, 243, 201),
                "star": (255, 249, 235),
                "cloud": (255, 255, 255),
                "hill": (219, 233, 205),
                "path": (241, 220, 181),
                "bush": (189, 222, 177),
                "shape_a": (255, 220, 178),
                "shape_b": (255, 203, 213),
                "shape_c": (201, 235, 246),
                "rabbit_body": (255, 251, 248),
                "rabbit_ear": (255, 213, 221),
                "rabbit_cloth": (118, 170, 224),
            },
            {
                "sky_top": (135, 193, 154),
                "sky_bottom": (238, 250, 242),
                "ground": (234, 228, 214),
                "accent": (77, 156, 113),
                "accent_soft": (204, 235, 217),
                "text_primary": (41, 77, 56),
                "text_secondary": (91, 120, 103),
                "moon": (255, 246, 196),
                "star": (255, 255, 240),
                "cloud": (255, 255, 255),
                "hill": (198, 229, 202),
                "path": (237, 220, 186),
                "bush": (147, 202, 157),
                "shape_a": (255, 226, 186),
                "shape_b": (189, 231, 214),
                "shape_c": (207, 216, 245),
                "rabbit_body": (255, 251, 248),
                "rabbit_ear": (255, 216, 224),
                "rabbit_cloth": (135, 164, 245),
            },
        ]
        theme = themes[(max(index, 1) - 1) % len(themes)]

        try:
            from PIL import Image, ImageDraw, ImageFont

            image = Image.new("RGB", (width, height), theme["sky_bottom"])
            draw = ImageDraw.Draw(image)

            font_candidates = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            ]

            def load_font(size: int):
                for p in font_candidates:
                    if Path(p).exists():
                        try:
                            return ImageFont.truetype(p, size=size)
                        except Exception:
                            pass
                return ImageFont.load_default()

            title_font = load_font(36)
            scene_font = load_font(30)
            body_font = load_font(22)
            meta_font = load_font(18)

            def draw_vertical_gradient(y0: int, y1: int, top_color, bottom_color):
                h = max(1, y1 - y0)
                for y in range(y0, y1):
                    ratio = (y - y0) / h
                    r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
                    g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
                    b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))

            def draw_cloud(x: int, y: int, scale: float = 1.0):
                c = theme["cloud"]
                draw.ellipse(
                    (x, y + 16 * scale, x + 90 * scale, y + 74 * scale), fill=c
                )
                draw.ellipse(
                    (x + 42 * scale, y, x + 132 * scale, y + 70 * scale), fill=c
                )
                draw.ellipse(
                    (x + 96 * scale, y + 18 * scale, x + 176 * scale, y + 78 * scale),
                    fill=c,
                )
                draw.rounded_rectangle(
                    (x + 28 * scale, y + 34 * scale, x + 142 * scale, y + 82 * scale),
                    radius=int(18 * scale),
                    fill=c,
                )

            def draw_star(cx: int, cy: int, radius: int):
                points = []
                for i in range(10):
                    angle = math.radians(-90 + i * 36)
                    r = radius if i % 2 == 0 else radius * 0.45
                    points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
                draw.polygon(points, fill=theme["star"])

            def draw_hill(x0: int, y0: int, x1: int, y1: int, color):
                draw.ellipse((x0, y0, x1, y1), fill=color)

            def draw_path(points, color):
                draw.line(points, fill=color, width=34, joint="curve")

            def draw_rabbit(x: int, y: int, scale: float = 1.0, pose: str = "stand"):
                body = theme["rabbit_body"]
                ear = theme["rabbit_ear"]
                cloth = theme["rabbit_cloth"]
                outline = (170, 154, 152)

                draw.ellipse(
                    (x + 18 * scale, y - 44 * scale, x + 42 * scale, y + 28 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )
                draw.ellipse(
                    (x + 48 * scale, y - 52 * scale, x + 72 * scale, y + 24 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )
                draw.ellipse(
                    (x + 25 * scale, y - 32 * scale, x + 35 * scale, y + 16 * scale),
                    fill=ear,
                )
                draw.ellipse(
                    (x + 55 * scale, y - 38 * scale, x + 65 * scale, y + 10 * scale),
                    fill=ear,
                )

                draw.ellipse(
                    (x, y, x + 86 * scale, y + 78 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )

                draw.ellipse(
                    (x + 26 * scale, y + 28 * scale, x + 32 * scale, y + 34 * scale),
                    fill=(68, 58, 58),
                )
                draw.ellipse(
                    (x + 52 * scale, y + 28 * scale, x + 58 * scale, y + 34 * scale),
                    fill=(68, 58, 58),
                )
                draw.ellipse(
                    (x + 38 * scale, y + 40 * scale, x + 48 * scale, y + 48 * scale),
                    fill=(255, 172, 180),
                )
                draw.arc(
                    (x + 32 * scale, y + 44 * scale, x + 54 * scale, y + 58 * scale),
                    start=10,
                    end=170,
                    fill=(120, 104, 110),
                    width=2,
                )

                body_y = y + 62 * scale
                draw.ellipse(
                    (x + 4 * scale, body_y, x + 96 * scale, body_y + 98 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )

                draw.rounded_rectangle(
                    (
                        x + 18 * scale,
                        body_y + 30 * scale,
                        x + 82 * scale,
                        body_y + 88 * scale,
                    ),
                    radius=int(18 * scale),
                    fill=cloth,
                )

                draw.line(
                    (
                        x + 18 * scale,
                        body_y + 46 * scale,
                        x - 12 * scale,
                        body_y + 70 * scale,
                    ),
                    fill=outline,
                    width=6,
                )
                draw.line(
                    (
                        x + 80 * scale,
                        body_y + 46 * scale,
                        x + 112 * scale,
                        body_y + 66 * scale,
                    ),
                    fill=outline,
                    width=6,
                )

                if pose == "walk":
                    draw.line(
                        (
                            x + 36 * scale,
                            body_y + 94 * scale,
                            x + 20 * scale,
                            body_y + 134 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )
                    draw.line(
                        (
                            x + 62 * scale,
                            body_y + 94 * scale,
                            x + 78 * scale,
                            body_y + 132 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )
                else:
                    draw.line(
                        (
                            x + 36 * scale,
                            body_y + 94 * scale,
                            x + 30 * scale,
                            body_y + 132 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )
                    draw.line(
                        (
                            x + 62 * scale,
                            body_y + 94 * scale,
                            x + 68 * scale,
                            body_y + 132 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )

                draw.ellipse(
                    (
                        x + 78 * scale,
                        body_y + 52 * scale,
                        x + 100 * scale,
                        body_y + 74 * scale,
                    ),
                    fill=body,
                    outline=outline,
                    width=2,
                )

            def draw_question_mark(x: int, y: int, color):
                draw.arc((x, y, x + 42, y + 42), start=200, end=20, fill=color, width=6)
                draw.line((x + 32, y + 30, x + 24, y + 48), fill=color, width=6)
                draw.ellipse((x + 19, y + 58, x + 27, y + 66), fill=color)

            def draw_arrow(x: int, y: int, color):
                draw.line((x, y, x + 80, y), fill=color, width=10)
                draw.polygon(
                    [(x + 80, y), (x + 52, y - 18), (x + 52, y + 18)], fill=color
                )

            draw_vertical_gradient(
                0, int(height * 0.76), theme["sky_top"], theme["sky_bottom"]
            )
            draw.rectangle((0, int(height * 0.72), width, height), fill=theme["ground"])

            draw_hill(-120, 430, 500, 820, theme["hill"])
            draw_hill(
                330,
                470,
                930,
                860,
                (theme["hill"][0] - 10, theme["hill"][1] - 8, theme["hill"][2] - 6),
            )
            draw_hill(760, 420, 1400, 850, theme["hill"])

            draw_path(
                [(130, 640), (300, 610), (500, 630), (760, 605), (1040, 640)],
                theme["path"],
            )

            moon_x = 980 if index == 1 else 1060 if index == 2 else 930
            moon_y = 84 if index == 1 else 102 if index == 2 else 78
            draw.ellipse(
                (moon_x, moon_y, moon_x + 120, moon_y + 120), fill=theme["moon"]
            )

            for sx, sy, sr in [
                (160, 88, 10),
                (280, 132, 8),
                (860, 62, 9),
                (1180, 180, 7),
                (1020, 236, 6),
            ]:
                draw_star(sx, sy, sr)

            draw_cloud(122, 116, 1.0)
            draw_cloud(708, 148, 0.85)

            if index == 1:
                draw_rabbit(250, 408, scale=1.8, pose="stand")
                draw_cloud(930, 206, 0.72)
                draw.rounded_rectangle(
                    (880, 520, 1160, 590), radius=22, fill=(255, 255, 255)
                )
                draw.text(
                    (910, 542), "晚安，小月亮", font=meta_font, fill=theme["accent"]
                )

            elif index == 2:
                draw_rabbit(200, 424, scale=1.7, pose="stand")
                draw_path(
                    [(480, 638), (610, 586), (740, 612)],
                    (231, 212, 180),
                )
                draw_path(
                    [(610, 586), (720, 522), (850, 510)],
                    (231, 212, 180),
                )
                draw_path(
                    [(610, 586), (724, 654), (860, 674)],
                    (231, 212, 180),
                )
                draw_question_mark(356, 318, theme["accent"])
                draw_question_mark(410, 282, theme["accent_soft"])
                draw.rounded_rectangle(
                    (860, 494, 1170, 594), radius=26, fill=(255, 255, 255)
                )
                draw.text(
                    (895, 520),
                    "要往哪边走呢？",
                    font=body_font,
                    fill=theme["text_primary"],
                )

            else:
                draw_rabbit(286, 420, scale=1.75, pose="walk")
                draw_arrow(804, 478, theme["accent"])
                draw.rounded_rectangle(
                    (934, 394, 1118, 468), radius=26, fill=(255, 255, 255)
                )
                draw.text(
                    (968, 420), "继续向前", font=body_font, fill=theme["text_primary"]
                )
                draw.ellipse(
                    (1032, 520, 1152, 640),
                    fill=(255, 236, 170),
                    outline=(229, 194, 92),
                    width=4,
                )
                draw.ellipse((1066, 552, 1118, 604), fill=(255, 255, 255))
                draw.rounded_rectangle(
                    (1068, 608, 1118, 642), radius=10, fill=(189, 160, 124)
                )

            draw.ellipse((60, 600, 220, 700), fill=theme["bush"])
            draw.ellipse((880, 612, 1080, 712), fill=theme["bush"])
            draw.ellipse(
                (1080, 624, 1230, 714),
                fill=(
                    theme["bush"][0] - 8,
                    theme["bush"][1] - 10,
                    theme["bush"][2] - 6,
                ),
            )

            overlay_x = 42
            overlay_y = 28
            draw.rounded_rectangle(
                (overlay_x, overlay_y, 510, 96), radius=26, fill=(255, 255, 255)
            )
            draw.text(
                (overlay_x + 24, overlay_y + 18),
                topic[:22],
                font=title_font,
                fill=theme["accent"],
            )

            draw.rounded_rectangle((42, 114, 340, 176), radius=20, fill=(255, 255, 255))
            draw.text(
                (64, 128),
                scene_title[:14] if scene_title else f"Scene {index}",
                font=scene_font,
                fill=theme["text_primary"],
            )
            draw.text(
                (250, 132),
                f"{index}/{max(1, int(self._scene_count(ctx.input.duration_sec)))}",
                font=meta_font,
                fill=theme["text_secondary"],
            )

            caption = visual_description or body_text
            caption_lines = textwrap.wrap(caption, width=28)[:2]
            if caption_lines:
                draw.rounded_rectangle(
                    (42, 606, 680, 686), radius=24, fill=(255, 255, 255)
                )
                cy = 622
                for line in caption_lines:
                    draw.text(
                        (66, cy), line, font=body_font, fill=theme["text_secondary"]
                    )
                    cy += 28

            if duration_sec > 0:
                draw.rounded_rectangle(
                    (1090, 620, 1218, 672), radius=18, fill=(255, 255, 255)
                )
                draw.text(
                    (1120, 636),
                    f"{duration_sec}S",
                    font=meta_font,
                    fill=theme["text_secondary"],
                )

            buffer = io.BytesIO()
            image.save(buffer, format="PPM")
            return buffer.getvalue()

        except Exception as e:
            print("[scene_ppm_fallback]", repr(e))

            safe_scene_label = f"SCENE {index:02d}"
            safe_footer = (
                f"{index}/{max(1, int(self._scene_count(ctx.input.duration_sec)))}"
            )

            def _ascii_text(value: str, default: str) -> str:
                normalized = "".join(
                    ch.upper() if 32 <= ord(ch) <= 126 else " "
                    for ch in str(value or "")
                )
                normalized = " ".join(normalized.split())
                return normalized or default

            safe_headline = _ascii_text(scene_title, "STORY FRAME")
            safe_body = _ascii_text(body_text, "WARM STORYBOARD FRAME")
            safe_meta = _ascii_text(
                f"{scene.get('shot_type', 'wide')} {scene.get('transition', 'fade')} {duration_sec}s",
                "WIDE FADE 15S",
            )
            safe_topic = _ascii_text(topic, "STORY VIDEO")

            pixels = bytearray(width * height * 3)

            def _set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
                if x < 0 or y < 0 or x >= width or y >= height:
                    return
                i = (y * width + x) * 3
                pixels[i] = color[0]
                pixels[i + 1] = color[1]
                pixels[i + 2] = color[2]

            def _fill_rect(
                x: int, y: int, w: int, h: int, color: tuple[int, int, int]
            ) -> None:
                x0 = max(0, x)
                y0 = max(0, y)
                x1 = min(width, x + w)
                y1 = min(height, y + h)
                for yy in range(y0, y1):
                    row = (yy * width + x0) * 3
                    for _ in range(x0, x1):
                        pixels[row] = color[0]
                        pixels[row + 1] = color[1]
                        pixels[row + 2] = color[2]
                        row += 3

            def _fill_circle(
                cx: int, cy: int, radius: int, color: tuple[int, int, int]
            ) -> None:
                r2 = radius * radius
                for yy in range(max(0, cy - radius), min(height, cy + radius + 1)):
                    for xx in range(max(0, cx - radius), min(width, cx + radius + 1)):
                        dx = xx - cx
                        dy = yy - cy
                        if dx * dx + dy * dy <= r2:
                            _set_pixel(xx, yy, color)

            FONT = {
                "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
                "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
                "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
                "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
                "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
                "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
                "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
                "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
                "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
                "J": ["00001", "00001", "00001", "00001", "10001", "10001", "01110"],
                "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
                "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
                "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
                "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
                "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
                "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
                "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
                "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
                "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
                "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
                "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
                "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
                "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
                "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
                "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
                "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
                "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
                "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
                "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
                "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
                "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
                "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
                "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
                "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
                "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
                "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
                " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
                "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
                "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
                ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
            }

            def _draw_char(
                x: int, y: int, ch: str, scale: int, color: tuple[int, int, int]
            ) -> int:
                pattern = FONT.get(ch, FONT[" "])
                for row_index, row_bits in enumerate(pattern):
                    for col_index, bit in enumerate(row_bits):
                        if bit == "1":
                            _fill_rect(
                                x + col_index * scale,
                                y + row_index * scale,
                                scale,
                                scale,
                                color,
                            )
                return 6 * scale

            def _draw_text(
                x: int, y: int, text: str, scale: int, color: tuple[int, int, int]
            ) -> None:
                cursor_x = x
                for ch in text:
                    cursor_x += _draw_char(cursor_x, y, ch, scale, color)

            for y in range(height):
                ratio = y / max(1, height - 1)
                r = int(
                    theme["sky_top"][0] * (1 - ratio) + theme["sky_bottom"][0] * ratio
                )
                g = int(
                    theme["sky_top"][1] * (1 - ratio) + theme["sky_bottom"][1] * ratio
                )
                b = int(
                    theme["sky_top"][2] * (1 - ratio) + theme["sky_bottom"][2] * ratio
                )
                _fill_rect(0, y, width, 1, (r, g, b))

            progress_ratio = min(
                1.0,
                max(
                    0.0, index / max(1, int(self._scene_count(ctx.input.duration_sec)))
                ),
            )

            _fill_rect(22, 22, width - 44, 72, theme["accent"])
            _fill_rect(38, 128, 280, height - 182, (255, 255, 255))
            _fill_rect(350, 150, 860, 400, (255, 255, 255))
            _fill_rect(350, 560, 860, 18, (232, 232, 238))
            _fill_rect(350, 560, int(860 * progress_ratio), 18, theme["accent"])

            _fill_circle(136, 242, 66, theme["shape_a"])
            _fill_circle(222, 334, 58, theme["shape_b"])
            _fill_rect(72, 540, 128, 64, theme["shape_c"])

            _draw_text(52, 44, safe_topic[:22], 3, (255, 255, 255))
            _draw_text(72, 420, safe_scene_label, 3, theme["accent"])
            _draw_text(72, 464, safe_meta[:18], 2, theme["text_secondary"])
            _draw_text(392, 192, safe_headline[:24], 3, theme["text_primary"])

            body_lines = textwrap.wrap(safe_body, width=34)[:3]
            if not body_lines:
                body_lines = ["WARM STORYBOARD FRAME"]

            text_y = 276
            for line in body_lines:
                _draw_text(392, text_y, line, 2, theme["text_secondary"])
                text_y += 38

            _draw_text(1100, 528, safe_footer, 2, theme["text_secondary"])

            data = bytearray()
            data.extend(f"P6\n{width} {height}\n255\n".encode("ascii"))
            data.extend(pixels)
            return bytes(data)

    def _run_image_assets(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        provider = self._image_provider_name()

        if provider == "pillow_storybook_renderer":
            return self._run_pillow_image_assets(ctx, outputs)

        if provider == "api_image_generator":
            try:
                return self._run_api_image_assets(ctx, outputs)
            except Exception as e:
                fallback_provider = self._image_fallback_provider_name()
                fallback_enabled = self._api_image_fallback_to_pillow()

                if (
                    fallback_enabled
                    and fallback_provider == "pillow_storybook_renderer"
                ):
                    fallback_result = self._run_pillow_image_assets(ctx, outputs)
                    fallback_result["fallback"] = {
                        "from_provider": "api_image_generator",
                        "to_provider": "pillow_storybook_renderer",
                        "reason": str(e),
                    }
                    return fallback_result

                raise RuntimeError(
                    f"image asset generation failed with provider={provider}: {e}"
                ) from e

        raise RuntimeError(f"unknown image provider: {provider}")

    def _run_pillow_image_assets(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        scene_by_id = {
            str(scene.get("scene_id")): scene
            for scene in scenes
            if scene.get("scene_id")
        }

        run_dir = self._ensure_image_run_dir(ctx.run_id)
        assets: List[Dict[str, Any]] = []

        if shot_items:
            for index, shot in enumerate(shot_items, start=1):
                shot_id = str(shot.get("shot_id") or f"shot_{index:02d}")
                scene_id = str(shot.get("scene_id") or "")
                scene_title = str(shot.get("scene_title") or f"Shot {index}")
                visual_description = str(shot.get("visual_description") or "").strip()
                shot_text = str(shot.get("text") or "").strip()
                shot_type = str(shot.get("shot_type") or "medium").strip()
                transition = str(shot.get("transition") or "fade").strip()

                pseudo_scene = {
                    "scene_id": shot_id,
                    "scene_title": scene_title,
                    "visual_description": visual_description,
                    "narration": shot_text,
                    "duration_sec": 0,
                    "shot_type": shot_type,
                    "transition": transition,
                }

                file_name = f"{shot_id}.ppm"
                output_path = run_dir / file_name
                output_path.write_bytes(self._build_scene_ppm(ctx, pseudo_scene, index))

                assets.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "file_name": file_name,
                        "relative_path": f"assets/mock/image/{ctx.run_id}/{file_name}",
                        "public_url": f"/assets/mock/image/{ctx.run_id}/{file_name}",
                        "mime_type": "image/x-portable-pixmap",
                        "status": "generated",
                    }
                )

            return {
                "enabled": True,
                "run_id": ctx.run_id,
                "provider": "pillow_storybook_renderer",
                "asset_count": len(assets),
                "assets": assets,
            }

        for index, scene in enumerate(scenes, start=1):
            scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
            file_name = f"{scene_id}.ppm"
            output_path = run_dir / file_name
            output_path.write_bytes(self._build_scene_ppm(ctx, scene, index))

            assets.append(
                {
                    "scene_id": scene_id,
                    "scene_title": scene.get("scene_title"),
                    "file_name": file_name,
                    "relative_path": f"assets/mock/image/{ctx.run_id}/{file_name}",
                    "public_url": f"/assets/mock/image/{ctx.run_id}/{file_name}",
                    "mime_type": "image/x-portable-pixmap",
                    "status": "generated",
                }
            )

        return {
            "enabled": True,
            "run_id": ctx.run_id,
            "provider": "pillow_storybook_renderer",
            "asset_count": len(assets),
            "assets": assets,
        }
    def _generate_api_image_bytes(
        self,
        *,
        prompt: str,
        scene: Dict[str, Any],
        scene_index: int,
    ) -> bytes:
        """
        Generate image bytes through SiliconFlow image generation API.

        Current implementation:
        - text-to-image only
        - request image URL from SiliconFlow
        - immediately download bytes because the returned URL is temporary
        """
        import json
        import urllib.error
        import urllib.request

        if not self._api_image_enabled():
            raise RuntimeError("API_IMAGE_ENABLED is false")

        api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("SILICONFLOW_API_KEY is not set")

        base_url = os.getenv(
            "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
        ).strip()
        if not base_url:
            base_url = "https://api.siliconflow.cn/v1"

        model = os.getenv("SILICONFLOW_IMAGE_MODEL", "Kwai-Kolors/Kolors").strip()
        if not model:
            model = "Kwai-Kolors/Kolors"

        image_size = os.getenv("SILICONFLOW_IMAGE_SIZE", "720x1280").strip()
        if not image_size:
            image_size = "720x1280"

        negative_prompt = os.getenv(
            "SILICONFLOW_IMAGE_NEGATIVE_PROMPT",
            "low quality, blurry, distorted anatomy, broken composition, extra limbs, duplicated subject, unreadable details",
        ).strip()

        num_inference_steps_raw = os.getenv("SILICONFLOW_IMAGE_STEPS", "20").strip()
        guidance_scale_raw = os.getenv("SILICONFLOW_IMAGE_GUIDANCE", "7.5").strip()

        try:
            num_inference_steps = int(num_inference_steps_raw)
        except ValueError:
            num_inference_steps = 20

        try:
            guidance_scale = float(guidance_scale_raw)
        except ValueError:
            guidance_scale = 7.5

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "image_size": image_size,
        }

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        # SiliconFlow docs indicate these parameters are applicable to Kolors.
        # Keep them for the default Kolors model and omit for other model families.
        if "kolors" in model.lower():
            payload["batch_size"] = 1
            payload["num_inference_steps"] = num_inference_steps
            payload["guidance_scale"] = guidance_scale

        request_url = f"{base_url.rstrip('/')}/images/generations"
        request_body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            request_url,
            data=request_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                response_text = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                error_body = repr(e)
            raise RuntimeError(
                f"SiliconFlow image generation failed with HTTP {e.code}: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"SiliconFlow image generation request failed: {e}"
            ) from e

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"SiliconFlow image generation returned invalid JSON: {response_text[:500]}"
            ) from e

        images = result.get("images") or []
        if not images:
            raise RuntimeError(
                f"SiliconFlow image generation returned no images: {response_text[:500]}"
            )

        first_image = images[0] or {}
        image_url = str(first_image.get("url") or "").strip()
        if not image_url:
            raise RuntimeError(
                f"SiliconFlow image generation returned empty image url: {response_text[:500]}"
            )

        download_request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
            method="GET",
        )

        last_error: Optional[Exception] = None
        image_bytes: bytes = b""

        for attempt in range(3):
            try:
                with urllib.request.urlopen(download_request, timeout=120) as response:
                    downloaded = response.read()

                if downloaded:
                    image_bytes = downloaded
                    break

                last_error = RuntimeError(
                    f"Generated image download returned empty bytes for scene {scene_index}"
                )
            except urllib.error.HTTPError as e:
                last_error = RuntimeError(
                    f"Generated image download failed with HTTP {e.code} for scene {scene_index}"
                )
            except urllib.error.URLError as e:
                last_error = RuntimeError(
                    f"Generated image download failed for scene {scene_index}: {e}"
                )
            except Exception as e:
                last_error = RuntimeError(
                    f"Generated image download failed for scene {scene_index}: {e}"
                )

            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))

        if not image_bytes:
            if last_error is not None:
                raise last_error
            raise RuntimeError(
                f"Generated image download returned empty bytes for scene {scene_index}"
            )

        return image_bytes

    def _run_api_image_assets(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        image_prompts = outputs.get("image_prompts") or {}
        prompt_items = image_prompts.get("prompts") or []

        prompt_by_shot_id = {
            str(item.get("shot_id")): str(item.get("prompt") or "").strip()
            for item in prompt_items
            if item.get("shot_id")
        }
        prompt_by_scene_id = {
            str(item.get("scene_id")): str(item.get("prompt") or "").strip()
            for item in prompt_items
            if item.get("scene_id")
        }

        run_dir = self._ensure_image_run_dir(ctx.run_id)
        assets: List[Dict[str, Any]] = []

        if shot_items:
            for index, shot in enumerate(shot_items, start=1):
                shot_id = str(shot.get("shot_id") or f"shot_{index:02d}")
                scene_id = str(shot.get("scene_id") or "")
                scene_title = str(shot.get("scene_title") or f"Shot {index}")
                prompt = prompt_by_shot_id.get(shot_id, "").strip()

                if not prompt:
                    text = str(shot.get("text", "")).strip()
                    visual_description = str(shot.get("visual_description", "")).strip()
                    prompt = visual_description or text or f"storybook shot {shot_id}"

                file_name = f"{shot_id}.png"
                output_path = run_dir / file_name

                pseudo_scene = {
                    "scene_id": shot_id,
                    "scene_title": scene_title,
                    "visual_description": shot.get("visual_description"),
                    "narration": shot.get("text"),
                    "shot_type": shot.get("shot_type"),
                    "transition": shot.get("transition"),
                }

                image_bytes = self._generate_api_image_bytes(
                    prompt=prompt,
                    scene=pseudo_scene,
                    scene_index=index,
                )
                if not isinstance(image_bytes, (bytes, bytearray)):
                    raise RuntimeError(
                        f"api image generator returned non-bytes payload for shot {shot_id}"
                    )
                output_path.write_bytes(image_bytes)

                assets.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "file_name": file_name,
                        "relative_path": f"assets/mock/image/{ctx.run_id}/{file_name}",
                        "public_url": f"/assets/mock/image/{ctx.run_id}/{file_name}",
                        "mime_type": "image/png",
                        "status": "generated",
                        "prompt": prompt,
                    }
                )

            return {
                "enabled": True,
                "run_id": ctx.run_id,
                "provider": "api_image_generator",
                "asset_count": len(assets),
                "assets": assets,
            }

        for index, scene in enumerate(scenes, start=1):
            scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
            prompt = prompt_by_scene_id.get(scene_id, "").strip()

            if not prompt:
                narration = str(scene.get("narration", "")).strip()
                visual_description = str(scene.get("visual_description", "")).strip()
                prompt = (
                    visual_description or narration or f"storybook scene {scene_id}"
                )

            file_name = f"{scene_id}.png"
            output_path = run_dir / file_name

            image_bytes = self._generate_api_image_bytes(
                prompt=prompt,
                scene=pseudo_scene,
                scene_index=index,
            )
            if not isinstance(image_bytes, (bytes, bytearray)):
                raise RuntimeError(
                    f"api image generator returned non-bytes payload for shot {shot_id}"
                )
            output_path.write_bytes(image_bytes)

            assets.append(
                {
                    "scene_id": scene_id,
                    "scene_title": scene.get("scene_title"),
                    "file_name": file_name,
                    "relative_path": f"assets/mock/image/{ctx.run_id}/{file_name}",
                    "public_url": f"/assets/mock/image/{ctx.run_id}/{file_name}",
                    "mime_type": "image/png",
                    "status": "generated",
                    "prompt": prompt,
                }
            )

        return {
            "enabled": True,
            "run_id": ctx.run_id,
            "provider": "api_image_generator",
            "asset_count": len(assets),
            "assets": assets,
        }
    def _run_video_prompts(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        return self._build_video_provider_prompts(ctx, scenes)

    def _run_dialogue_script(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        voice_mode = self._normalized_voice_mode(ctx.input.voice_mode)
        speaker_profiles = self._speaker_profiles(ctx)

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

            character_profiles = self._character_speaker_profiles(ctx)
            main_character_speaker = self._character_speaker_name(ctx)
            secondary_character_speaker = self._secondary_character_speaker_name(ctx)

            for index, shot in enumerate(shot_items, start=1):
                text = str(shot.get("audio_text") or shot.get("text") or "").strip()
                if not text:
                    continue

                resolved = self._resolve_character_speaker(ctx, text)

                lines.append(
                    self._build_dialogue_line(
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

            for index, scene in enumerate(scenes, start=1):
                text = str(scene.get("narration", "")).strip()
                if not text:
                    continue

                segments = [part.strip() for part in text.split("。") if part.strip()]
                if not segments:
                    segments = [text]

                for seg_index, segment in enumerate(segments, start=1):
                    speaker = alternating_speakers[
                        (seg_index - 1) % len(alternating_speakers)
                    ]
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

        character_profiles = self._character_speaker_profiles(ctx)
        main_character_speaker = self._character_speaker_name(ctx)
        secondary_character_speaker = self._secondary_character_speaker_name(ctx)

        for index, scene in enumerate(scenes, start=1):
            text = str(scene.get("narration", "")).strip()
            if not text:
                continue

            segments = [part.strip() for part in text.split("。") if part.strip()]
            if not segments:
                segments = [text]

            for seg_index, segment in enumerate(segments, start=1):
                final_text = f"{segment}。"
                resolved = self._resolve_character_speaker(ctx, final_text)

                lines.append(
                    self._build_dialogue_line(
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
    def _run_audio_segments(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        dialogue_script = outputs.get("dialogue_script") or {}
        lines = dialogue_script.get("lines") or []

        if not dialogue_script.get("enabled") or not lines:
            empty_directory_manifest = self._write_audio_directory_manifest(
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
        run_dir = self._ensure_audio_run_dir(ctx.run_id)

        tts_enabled = self._tts_enabled()
        fallback_to_mock = self._tts_fallback_to_mock()
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
                    tts_result = self._generate_real_tts_audio(
                        text=text,
                        speaker=speaker,
                        voice_style=voice_style,
                        output_path=output_path,
                    )
                    generation_provider = str(
                        tts_result.get("provider", self._tts_provider_name())
                    )
                    generation_status = "generated"
                    asset_status = "generated"
                    generation_mode = "real_tts"

                    actual_duration_sec = self._probe_audio_duration_seconds(output_path)
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

        directory_manifest = self._write_audio_directory_manifest(ctx.run_id, assets)
        scene_asset_map = self._group_audio_assets_by_scene(assets)

        overall_provider = (
            self._tts_provider_name() if real_generation_count > 0 else "mock_tts"
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
    def _run_narration(
        self, ctx: StepContext, outputs: Dict[str, Any]
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

    def _run_subtitles(
        self, ctx: StepContext, outputs: Dict[str, Any]
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
    def _run_render_plan(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        subtitles = outputs.get("subtitles") or {}
        subtitles_enabled = bool(subtitles.get("enabled"))

        return self._build_render_plan_by_provider(ctx, scenes, subtitles_enabled)

    def _build_video_concat_file(
        self,
        ctx: StepContext,
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
        video_run_dir = self._ensure_video_run_dir(ctx.run_id)
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

            image_path = PROJECT_ROOT / str(image_asset.get("relative_path"))
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
    def _run_final_video(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        image_assets = outputs.get("image_assets") or {}
        audio_segments = outputs.get("audio_segments") or {}
        subtitles = outputs.get("subtitles") or {}

        image_asset_list = image_assets.get("assets") or []
        audio_item_list = audio_segments.get("items") or []

        if not image_asset_list or not audio_item_list:
            return {
                "enabled": False,
                "status": "skipped",
                "reason": "missing image_assets or audio_segments",
            }

        total_duration_sec = 0.0
        for item in audio_item_list:
            duration_sec = float(item.get("duration_sec") or 0.0)
            if duration_sec <= 0:
                duration_sec = float(item.get("duration_estimate_sec") or 0.0)
            total_duration_sec += max(duration_sec, 0.0)

        video_run_dir = self._ensure_video_run_dir(ctx.run_id)
        concat_file = self._build_video_concat_file(ctx, image_assets, audio_segments)

        audio_manifest = audio_segments.get("asset_manifest") or {}
        audio_assets = audio_manifest.get("assets") or []
        audio_file_paths = [
            str(PROJECT_ROOT / str(asset.get("relative_path")))
            for asset in audio_assets
            if asset.get("relative_path")
        ]

        if not audio_file_paths:
            return {
                "enabled": False,
                "status": "skipped",
                "reason": "no audio files available",
            }

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
            capture_output=True,
            text=True,
        )

        subtitle_path = video_run_dir / "subtitles.srt"
        subtitle_path.write_text(
            str(subtitles.get("srt_preview", "")).strip() + "\n",
            encoding="utf-8",
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
            capture_output=True,
            text=True,
        )

        final_video_path = video_run_dir / "final.mp4"

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
            capture_output=True,
            text=True,
        )

        return {
            "enabled": True,
            "status": "generated",
            "run_id": ctx.run_id,
            "file_name": "final.mp4",
            "relative_path": f"assets/mock/video/{ctx.run_id}/final.mp4",
            "public_url": f"/assets/mock/video/{ctx.run_id}/final.mp4",
            "duration_sec": round(total_duration_sec, 3),
            "audio_track_path": f"assets/mock/video/{ctx.run_id}/merged_audio.mp3",
            "subtitle_path": f"assets/mock/video/{ctx.run_id}/subtitles.srt",
        }