from __future__ import annotations

import shutil
import json
import ast
import re
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
from app.services.runner_audio_render_support import RunnerAudioRenderSupport
from app.services.runner_character_manifest import RunnerCharacterManifestSupport
from app.services.runner_errors import UnknownStepError, UnknownVideoProviderError
from app.services.runner_image_review import RunnerImageReviewSupport
from app.services.runner_image_selection_support import RunnerImageSelectionSupport
from app.services.runner_render_plan import RunnerRenderPlanSupport
from app.services.runner_scene_characters import RunnerSceneCharactersSupport
from app.services.runner_session import RunnerSessionStore
from app.services.runner_story_support import RunnerStorySupport
from app.services.runner_story_text import RunnerStoryTextSupport
from app.services.runner_storyboard import RunnerStoryboardSupport
from app.services.runner_video_prompts import RunnerVideoPromptsSupport
from app.services.image_provider_queue import ImageProviderQueue
from app.services.image_provider_adapter import ApiImageGeneratorAdapter
from app.services.image_provider_types import ImageGenerationTask
from app.services.image_candidate_selector import select_best_candidate
from app.services.character_visual_profile_llm import (
    build_llm_character_visual_profile,
    build_llm_character_visual_profiles,
)
from app.services.image_prompt_policy import (
    build_image_prompt_policy_blocks,
    clean_image_prompt_text,
)
from app.services.runner_single_scene_image_support import RunnerSingleSceneImageSupport
from app.services.topic_character_infer import infer_primary_character_manifest
from app.services.story_subject_extractor import (
    extract_story_subjects,
    story_main_subject,
)
from app.services.llm_output_sanitizer import parse_story_payload


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
DEFAULT_LLM_API_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_STORY_PROVIDER = "template"  # template | openai_compatible_llm
DEFAULT_STORY_MODEL = ""
DEFAULT_STORY_TIMEOUT_SECONDS = 60


class WorkflowRunner:

    def _run_video_audio_render_plan(self, run_input: dict, outputs: dict):
        if hasattr(self, "rerender_final_video"):
            self.rerender_final_video(
                workflow_id=run_input.get("workflow_id"),
                session_id=run_input.get("session_id"),
                run_id=outputs.get("run_id"),
                workflow_input=run_input,
                image_assets=outputs.get("image_assets"),
                audio_segments=outputs.get("audio_segments"),
                subtitles=outputs.get("subtitles"),
            )

    def _run_async(self, run_input: dict, callback: callable):
        import threading
        import traceback
        from app.schemas.workflow import WorkflowRunRequest

        def _task():
            try:
                request = WorkflowRunRequest(**run_input)
                result = self.run(request)
                if hasattr(result, "model_dump"):
                    payload = result.model_dump()
                elif isinstance(result, dict):
                    payload = result
                else:
                    payload = dict(result)
                callback(payload)
            except Exception as error:
                print("[AsyncRunner] task failed:", error)
                traceback.print_exc()

        threading.Thread(
            target=_task,
            daemon=True,
            name="RunnerAsyncWorker",
        ).start()

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
        self._audio_render_support = RunnerAudioRenderSupport(self)
        self._character_manifest_support = RunnerCharacterManifestSupport(self)
        self._image_selection_support = RunnerImageSelectionSupport(self)
        self._image_review = RunnerImageReviewSupport(self)
        self._render_plan = RunnerRenderPlanSupport(self)
        self._scene_characters = RunnerSceneCharactersSupport(self)
        self._single_scene_image_support = RunnerSingleSceneImageSupport(self)
        self._story_support = RunnerStorySupport(self)
        self._story_text = RunnerStoryTextSupport(self)
        self._storyboard = RunnerStoryboardSupport(self)
        self._video_prompts = RunnerVideoPromptsSupport(self)

        self._handlers = {
            "story": self._run_story,
            "storyboard": self._run_storyboard,
            "sentence_shots": self._run_sentence_shots,
            "image_prompts": self._run_image_prompts,
            "image_assets": self._run_image_assets,
            "video_prompts": self._run_video_prompts,
            "dialogue_script": self._audio_render_support.run_dialogue_script,
            "audio_segments": self._audio_render_support.run_audio_segments,
            "narration": self._audio_render_support.run_narration,
            "subtitles": self._audio_render_support.run_subtitles,
            "render_plan": self._run_render_plan,
            "final_video": self._audio_render_support.run_final_video,
        }
        self._session = RunnerSessionStore()

    def _workflow_input_from_dict(
        self, workflow_input: Dict[str, Any]
    ) -> WorkflowInput:
        if isinstance(workflow_input, WorkflowInput):
            return workflow_input
        if not isinstance(workflow_input, dict):
            workflow_input = {}
        return WorkflowInput(**workflow_input)

    def _build_step_context(
        self,
        *,
        workflow_id: str,
        session_id: Optional[str],
        run_id: str,
        workflow_input: WorkflowInput,
    ) -> StepContext:
        return StepContext(
            workflow_id=workflow_id,
            session_id=session_id,
            run_id=run_id,
            input=workflow_input,
        )

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
        return self._audio_render_support.rerender_final_video(
            workflow_id=workflow_id,
            session_id=session_id,
            run_id=run_id,
            workflow_input=workflow_input,
            image_assets=image_assets,
            audio_segments=audio_segments,
            subtitles=subtitles,
        )

    def build_image_assets_from_selected_assets(
        self,
        *,
        run_id: str,
        image_review: Dict[str, Any],
        provider: str,
    ) -> Dict[str, Any]:
        return self._image_selection_support.build_image_assets_from_selected_assets(
            run_id=run_id,
            image_review=image_review,
            provider=provider,
        )

    def get_real_kling_samples_manifest(self) -> Dict[str, Any]:
        manifest = self._render_plan.build_real_samples_manifest()
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

    def _llm_api_base_url(self) -> str:
        # 优先走 OPENAI_BASE_URL（你们项目一直按 openai-compatible 使用）
        base = (
            os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_API_BASE_URL") or ""
        ).strip()
        return base or DEFAULT_LLM_API_BASE_URL

    def _llm_api_key(self) -> str:
        return (os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()

    def _story_provider_name(self) -> str:
        return (os.getenv("STORY_PROVIDER") or DEFAULT_STORY_PROVIDER).strip()

    def _story_model_name(self) -> str:
        # 不瞎猜你具体模型名：优先读你显式配置，其次读常见环境变量
        model = (
            (os.getenv("STORY_MODEL") or "").strip()
            or (os.getenv("OPENAI_MODEL") or "").strip()
            or (os.getenv("LLM_MODEL") or "").strip()
            or DEFAULT_STORY_MODEL
        )
        return model

    def _story_timeout_seconds(self) -> int:
        raw = (os.getenv("STORY_TIMEOUT_SECONDS") or "").strip()
        if raw.isdigit():
            return max(5, min(180, int(raw)))
        return DEFAULT_STORY_TIMEOUT_SECONDS

    def _generate_story_with_llm(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, str]:
        api_key = self._llm_api_key()
        if not api_key:
            raise RuntimeError("LLM api key is missing (OPENAI_API_KEY/LLM_API_KEY)")

        model = self._story_model_name()
        if not model:
            raise RuntimeError("STORY_MODEL/OPENAI_MODEL/LLM_MODEL is missing")

        topic = (ctx.input.topic or "").strip() or "一个温暖的童话故事"
        tone_label = self._tone_label(ctx.input.tone)
        audience_label = self._audience_label(ctx.input.audience)
        story_plan = self._duration_story_plan(ctx.input.duration_sec)

        manifest_items = self._character_manifest_support.character_manifest_items(
            outputs
        )
        character_hint = ""
        if manifest_items:
            parts = []
            for item in manifest_items:
                display = str(item.get("display_name") or "").strip()
                species = str(item.get("species") or "").strip()
                role = str(item.get("role_type") or "").strip()
                traits = str(item.get("visual_traits") or "").strip()
                forbid = str(item.get("forbidden_traits") or "").strip()
                parts.append(
                    f"- {display or species or '角色'}：请在故事中自然出现并参与情节；"
                    f"{('物种是' + species + '；') if species else ''}"
                    f"{('外观特征：' + traits + '；') if traits else ''}"
                    f"{('禁止出现：' + forbid + '；') if forbid else ''}"
                )
            character_hint = "\n".join(parts)

        system_prompt = (
            "You are a professional children's story writer.\n"
            "Write in Chinese.\n"
            "Return ONLY the story text. No JSON, no markdown, no headings."
        )

        user_prompt = (
            f"Topic: {topic}\n"
            f"Tone: {tone_label}\n"
            f"Audience: {audience_label}\n"
            f"Visual style: {ctx.input.visual_style}\n"
            f"Character style: {ctx.input.character_style}\n"
            f"Language: {ctx.input.language}\n"
            f"Selected duration: {story_plan['duration_sec']} seconds\n"
            f"Target Chinese story length: {story_plan['target_min_chars']}-{story_plan['target_max_chars']} Chinese characters, about {story_plan['target_chars']} Chinese characters.\n"
            f"Expected narration: enough complete narration for about {story_plan['duration_sec']} seconds and {story_plan['scene_count']} scenes.\n"
            f"Constraints:\n"
            f"- The plot must meaningfully reflect the topic (not a generic template).\n"
            f"- Generate enough story content for the selected duration.\n"
            f"- Provide a complete structure: beginning, development, problem or discovery, action, resolution, and warm ending.\n"
            f"- Do not repeat sentences or adjacent ideas.\n"
            f"- Do not include scene numbers, bullet points, markdown, JSON, or section headings.\n"
            f"- Never use technical/chat role words such as 'user', 'assistant', 'system', or 'role' as character names or story content.\n"
            f"- If character input contains technical words such as user/assistant/system, ignore them and infer natural child-friendly character names from the topic.\n"
            f"- Do NOT output any tokens like 'role=', 'species=', 'traits=', 'forbid='.\n"
            f"Characters (if provided):\n{character_hint or '- (none)'}\n"
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 1400,
        }

        req = urllib_request.Request(
            url=f"{self._llm_api_base_url().rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib_request.urlopen(req, timeout=self._story_timeout_seconds()) as resp:
            raw = resp.read()

        if not raw:
            raise RuntimeError("LLM response is empty")

        data = json.loads(raw.decode("utf-8", errors="ignore"))
        content = (
            (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
            or ""
        ).strip()

        if not content:
            raise RuntimeError("LLM content is empty")

        title = f"{topic}的故事"
        summary = f"一个围绕“{topic}”展开的短篇故事，整体气质{tone_label}，适合做成{audience_label}向内容。"

        parsed = parse_story_payload(content, topic=topic)
        text = parsed["text"] if parsed and parsed.get("text") else content

        return {
            "title": title.strip(),
            "summary": summary.strip(),
            "text": text.strip(),
        }

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
        # NOTE: Do NOT create directories here.
        # We create parent dirs only when we actually write an output file.
        # This prevents leaving lots of empty run dirs when generation/refresh fails.
        run_dir = MOCK_IMAGE_ROOT / run_id
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

        previous_session_data = self._session.get_session_data(req.session_id)

        step_results: List[StepResult] = []

        character_candidates = self._character_manifest_support.build_character_candidates(
            req.input
        )
        character_manifest = self._character_manifest_support.build_character_manifest(
            req.input, character_candidates
        )

        # P0-05: structured_characters_enabled=false 时，按 topic 自动补角色 manifest。
        # 支持 primary + N supporting subjects，避免多角色主题只出现第一个角色。
        if (not req.input.structured_characters_enabled) and (not character_manifest):
            extracted_subjects = extract_story_subjects(req.input.topic)
            auto_manifest: List[Dict[str, Any]] = []

            for index, subject in enumerate(extracted_subjects.all_subjects, start=1):
                role_type = "primary" if index == 1 else "secondary"
                character_id = (
                    "char_primary_01"
                    if role_type == "primary"
                    else f"char_secondary_{index - 1:02d}"
                )
                auto_manifest.append(
                    {
                        "character_id": character_id,
                        "display_name": subject,
                        "species": subject,
                        "role_type": role_type,
                        "signature_traits": [],
                        "forbidden_traits": [],
                        "locking_level": "strict",
                        "reference_assets": {
                            "status": "pending",
                            "front_view": None,
                            "side_view": None,
                            "three_quarter_view": None,
                        },
                        "source": "story_subject_extractor",
                    }
                )

            if auto_manifest:
                character_manifest = auto_manifest
            else:
                inferred_primary = infer_primary_character_manifest(req.input.topic)
                if inferred_primary is not None:
                    character_manifest = [inferred_primary]

        character_manifest = self._character_manifest_support.enrich_character_manifest_traits_from_topic(
            character_manifest,
            req.input.topic,
        )

        aggregated_outputs: Dict[str, Any] = {
            "character_candidates": {
                "enabled": bool(req.input.structured_characters_enabled),
                "count": len(character_candidates),
                "items": character_candidates,
            },
            "character_manifest": {
                "enabled": bool(req.input.structured_characters_enabled)
                or bool(character_manifest),
                "count": len(character_manifest),
                "characters": character_manifest,
            },
        }

        for step in req.steps:
            name = step.name.strip()
            handler = self._handlers.get(name)
            if handler is None:
                raise UnknownStepError(f"Unknown step: {name}")

            if name == "image_assets":
                output = self._image_review.build_deferred_image_assets_output(ctx)
            else:
                output = handler(ctx, aggregated_outputs)

            step_results.append(
                StepResult(name=name, status="COMPLETED", output=output)
            )
            aggregated_outputs[name] = output

            if name == "image_assets":
                aggregated_outputs["image_review"] = self._image_review.build_pending_image_review(
                    reason="waiting_for_manual_refresh"
                )
            elif name == "video_prompts":
                video_prompt_status = str(output.get("status") or "").strip().lower()
                if (
                    video_prompt_status == "pending"
                    and "image_review" not in aggregated_outputs
                ):
                    aggregated_outputs["image_review"] = (
                        self._image_review.build_pending_image_review()
                    )

        self._session.save_run_context(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=run_id,
            outputs=aggregated_outputs,
            workflow_input=req.input.model_dump(),
        )

        # 落盘 outputs.json：不依赖外部异步回调，保证流程结束后磁盘一定有完整产物
        try:
            out_dir = PROJECT_ROOT / "assets" / "mock" / str(req.workflow_id)
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / "outputs.json", "w", encoding="utf-8") as f:
                json.dump(
                    aggregated_outputs,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
        except Exception as error:
            print(f"[WorkflowRunner] write outputs.json failed: {error}")

        session_memory_summary = self._session.build_session_memory_summary(
            req.session_id,
            previous_session_data,
            aggregated_outputs,
        )
        self._session.save_session_data(req, aggregated_outputs)
        render_package = self._render_plan.build_render_package(ctx, aggregated_outputs)

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

        character_anchor = self._character_consistency_anchor(ctx, outputs)

        prompts: List[Dict[str, Any]] = []
        character_visual_profile: Dict[str, Any] = build_llm_character_visual_profile(
            self,
            ctx,
            outputs,
            subject_hint=character_anchor,
        )
        character_visual_profiles: Dict[str, Any] = build_llm_character_visual_profiles(
            self,
            ctx,
            outputs,
        )

        enriched_character_manifest = self._character_manifest_support.apply_visual_profiles_to_character_manifest(
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
                character_block = self._scene_characters.scene_character_prompt_block(
                    outputs, scene_data
                )
                scene_required_presence_block = (
                    self._scene_characters.scene_character_required_presence_block(
                        outputs, scene_data
                    )
                )
                negative_block = self._scene_characters.scene_character_negative_block(
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

                prompt = ", ".join(
                    part
                    for part in [
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
                    if part
                )

                prompts.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "characters": scene_data.get("characters") or [],
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

            character_block = self._scene_characters.scene_character_prompt_block(
                outputs, scene
            )
            scene_required_presence_block = (
                self._scene_characters.scene_character_required_presence_block(
                    outputs, scene
                )
            )
            negative_block = self._scene_characters.scene_character_negative_block(
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

            prompt = ", ".join(
                part
                for part in [
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
                if part
            )

            prompts.append(
                {
                    "scene_id": scene_id,
                    "scene_title": scene_title,
                    "characters": self._scene_characters.enriched_scene_characters_from_manifest(
                        outputs,
                        scene,
                    ),
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

    def _scene_count(self, duration_sec: int) -> int:
        return self._story_text.scene_count(duration_sec)

    def _duration_story_plan(self, duration_sec: int) -> Dict[str, int]:
        return self._story_text.duration_story_plan(duration_sec)

    def _sanitize_llm_story_text(self, text: str, topic: str = "") -> str:
        return self._story_text.sanitize_llm_story_text(text, topic)

    def _story_text_has_blocked_tokens(self, text: str) -> bool:
        return self._story_text.story_text_has_blocked_tokens(text)

    def _story_text_char_count(self, text: str) -> int:
        return self._story_text.story_text_char_count(text)

    def _story_text_has_quality_issues(self, text: str) -> bool:
        return self._story_text.story_text_has_quality_issues(text)

    def _audience_label(self, audience: str) -> str:
        return self._story_text.audience_label(audience)

    def _tone_label(self, tone: str) -> str:
        return self._story_text.tone_label(tone)

    def _visual_style_label(self, visual_style: str) -> str:
        return self._story_text.visual_style_label(visual_style)

    def _character_style_label(self, character_style: str) -> str:
        return self._story_text.character_style_label(character_style)

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
        """
        Decide whether API image generation should fallback to Pillow.
        Controlled by env KLING_IMAGE_FALLBACK_TO_PILLOW:
        - "1", "true", "yes", "on" => allow fallback
        - any other / default => disable fallback
        """
        import os

        value = os.getenv("KLING_IMAGE_FALLBACK_TO_PILLOW", "false").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _image_api_key(self) -> str:
        image_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
        if image_key:
            return image_key
        return os.getenv("OPENAI_API_KEY", "").strip()

    def _image_api_base_url(self) -> str:
        value = os.getenv("SILICONFLOW_BASE_URL", "").strip()
        if value:
            return value.rstrip("/")

        value = os.getenv("OPENAI_BASE_URL", "").strip()
        if value:
            return value.rstrip("/")

        return "https://api.siliconflow.cn/v1"

    def _image_429_strategy(self) -> str:
        value = os.getenv("IMAGE_429_STRATEGY", "pillow_fallback").strip().lower()
        if value in {"pending", "pillow_fallback"}:
            return value
        return "pillow_fallback"

    def _is_rate_limit_error(self, error: Exception) -> bool:
        text = str(error or "").lower()
        return (
            "429" in text
            or "rate limit" in text
            or "too many requests" in text
            or "ipm limit" in text
            or "ipd limit" in text
        )

    def _force_image_rate_limit(self) -> bool:
        value = os.getenv("FORCE_IMAGE_RATE_LIMIT", "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _build_pending_image_assets_result(
        self,
        *,
        ctx: StepContext,
        provider: str,
        reason: str,
        retry_after_sec: int = 60,
    ) -> Dict[str, Any]:
        # pending 阶段没有真实候选，candidate_scores 统一返回空列表，避免下游按字段直接取值时崩溃
        normalized_reason = str(reason or "").strip() or "rate_limited"
        return {
            "enabled": False,
            "run_id": ctx.run_id,
            "provider": provider,
            "status": "retrying",
            "retryable": True,
            "retry_after_sec": retry_after_sec,
            "reason": normalized_reason,
            "detail": reason,
            "asset_count": 0,
            "assets": [],
            "candidate_scores": [],
        }

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

    def _resolve_character_speaker(self, ctx: StepContext, text: str) -> Dict[str, str]:
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

    def _resolved_image_asset_ref(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        selected_asset_ref = asset.get("selected_asset_ref") or {}
        if isinstance(selected_asset_ref, dict) and selected_asset_ref:
            return selected_asset_ref

        candidate_asset_refs = asset.get("candidate_asset_refs") or []
        if isinstance(candidate_asset_refs, list) and candidate_asset_refs:
            first_ref = candidate_asset_refs[0]
            if isinstance(first_ref, dict):
                return first_ref

        fallback = {
            "scene_id": asset.get("scene_id"),
            "shot_id": asset.get("shot_id"),
            "file_name": asset.get("file_name"),
            "relative_path": asset.get("relative_path"),
            "public_url": asset.get("public_url"),
            "mime_type": asset.get("mime_type"),
            "provider": asset.get("provider"),
        }
        return {
            key: value
            for key, value in fallback.items()
            if value is not None and value != ""
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

    def _clean_story_topic(self, topic: str) -> str:
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

    def _topic_primary_character_display_label(self, ctx: StepContext) -> str:
        topic = self._clean_story_topic(ctx.input.topic)
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

    def _main_character_display_label(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        # 1️⃣ manifest 优先
        if outputs:
            manifest_item = (
                self._character_manifest_support.manifest_character_by_role(
                    outputs, "primary"
                )
            )
            if manifest_item is not None:
                display_value = str(manifest_item.get("display_name") or "").strip()
                if display_value:
                    return display_value

        # 2️⃣ 手填
        display_value = str(
            getattr(ctx.input, "main_character_display", "") or ""
        ).strip()
        if display_value:
            return display_value

        main_value = str(getattr(ctx.input, "main_character", "") or "").strip()
        if main_value:
            return main_value

        # 3️⃣ 从 topic 中提取主角，避免把完整主题当成角色名
        topic_character = self._topic_primary_character_display_label(ctx)
        if topic_character:
            return topic_character

        # 4️⃣ 最终 fallback
        return self._character_style_label(ctx.input.character_style)

    def _secondary_character_display_label(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        if outputs:
            manifest_item = (
                self._character_manifest_support.manifest_character_by_role(
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

    def _has_secondary_character(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return bool(self._secondary_character_display_label(ctx, outputs))

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

    def _visual_subject_constraints(self, subject: str) -> str:
        value = str(subject or "").strip()
        if not value:
            return ""

        if "蝌蚪" in value:
            return (
                "tadpole, round head, long tail, swimming in water, "
                "no frog legs, no adult frog body, not a frog"
            )

        return ""

    def _character_consistency_anchor(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        explicit_anchor = str(
            getattr(ctx.input, "character_consistency_anchor", "") or ""
        ).strip()
        if explicit_anchor:
            return explicit_anchor

        # ✅ 1) 优先走 character_manifest（primary 角色锚点）
        primary = None
        if outputs:
            primary = self._character_manifest_support.manifest_character_by_role(
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

        # ✅ 2) 其次走 ctx.input.main_character，但跳过泛化默认值
        main_character = str(getattr(ctx.input, "main_character", "") or "").strip()
        generic_subjects = {
            "",
            "animal protagonist",
            "protagonist",
            "character",
        }
        if main_character and main_character.lower() not in generic_subjects:
            visual_constraints = self._visual_subject_constraints(main_character)
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

        # ✅ 3) 开放式 topic 主角兜底：小汽车 / 小蝌蚪 / 小鼹鼠 / 小机器人 / 小云朵
        derived_subject = self._main_character_display_label(ctx, outputs)
        if derived_subject and derived_subject.lower() not in generic_subjects:
            visual_constraints = self._visual_subject_constraints(derived_subject)
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

        # ✅ 4) 最终兜底才使用 character_style，避免默认 animal 覆盖真实主角
        return (
            f"main subject: {ctx.input.character_style} protagonist, "
            "same main subject across all scenes, "
            "consistent visual identity, "
            "consistent body shape, "
            "cute expressive face, "
            "storybook details"
        )

        # ✅ 3) 最后兜底（旧逻辑保留）
        return (
            f"{ctx.input.character_style} protagonist, "
            "same character across all scenes, "
            "consistent facial features, "
            "consistent body shape, "
            "consistent outfit and visual identity, "
            "cute expressive face, "
            "storybook details"
        )

    def _build_story_paragraphs(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        return self._story_text.build_story_paragraphs(ctx, outputs)

    def _expand_scene_blueprints(
        self,
        base: List[Dict[str, str]],
        scene_count: int,
    ) -> List[Dict[str, str]]:
        if scene_count <= 0:
            return []
        if not base:
            return []

        expanded: List[Dict[str, str]] = []
        for index in range(scene_count):
            source = base[index % len(base)]
            cycle = index // len(base)
            item = dict(source)
            if cycle > 0:
                item["scene_title"] = (
                    f"{source.get('scene_title', '故事片段')} · 延展 {cycle + 1}"
                )
            expanded.append(item)

        return expanded

    def _scene_blueprints(
        self,
        ctx: StepContext,
        scene_count: int,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        tone_label = self._tone_label(ctx.input.tone)
        visual_label = self._visual_style_label(ctx.input.visual_style)
        main_character_display = self._main_character_display_label(ctx, outputs)
        secondary_character_display = self._secondary_character_display_label(
            ctx, outputs
        )
        has_secondary_character = self._has_secondary_character(ctx, outputs)

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
            return self._expand_scene_blueprints(base, scene_count)

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
        return self._expand_scene_blueprints(base, scene_count)

    def _image_asset_by_scene_id(
        self, outputs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        image_assets = outputs.get("image_assets") or {}
        assets = image_assets.get("assets") or []

        mapping: Dict[str, Dict[str, Any]] = {}
        for item in assets:
            if not isinstance(item, dict):
                continue
            scene_id = str(item.get("scene_id") or "").strip()
            if scene_id:
                mapping[scene_id] = item
        return mapping

    def _image_asset_ref_from_item(
        self,
        item: Dict[str, Any],
        provider: str,
    ) -> Dict[str, Any]:
        return {
            "scene_id": item.get("scene_id"),
            "file_name": item.get("file_name"),
            "relative_path": item.get("relative_path"),
            "public_url": item.get("public_url"),
            "mime_type": item.get("mime_type"),
            "provider": provider,
        }

    def _build_mock_candidate_asset_refs(
        self,
        item: Dict[str, Any],
        provider: str,
    ) -> List[Dict[str, Any]]:
        primary_ref = self._image_asset_ref_from_item(item, provider)

        relative_path = str(item.get("relative_path") or "").strip()
        public_url = str(item.get("public_url") or "").strip()
        file_name = str(item.get("file_name") or "").strip()
        scene_id = item.get("scene_id")
        mime_type = item.get("mime_type")

        if not relative_path or not public_url or not file_name:
            return [primary_ref]

        if "." in file_name:
            file_stem, file_ext = file_name.rsplit(".", 1)
            mock_file_name = f"{file_stem}__candidate_b.{file_ext}"
        else:
            mock_file_name = f"{file_name}__candidate_b"

        if "." in relative_path:
            relative_stem, relative_ext = relative_path.rsplit(".", 1)
            mock_relative_path = f"{relative_stem}__candidate_b.{relative_ext}"
        else:
            mock_relative_path = f"{relative_path}__candidate_b"

        if "." in public_url:
            public_stem, public_ext = public_url.rsplit(".", 1)
            mock_public_url = f"{public_stem}__candidate_b.{public_ext}"
        else:
            mock_public_url = f"{public_url}__candidate_b"

        mock_ref = {
            "scene_id": scene_id,
            "file_name": mock_file_name,
            "relative_path": mock_relative_path,
            "public_url": mock_public_url,
            "mime_type": mime_type,
            "provider": f"{provider}_mock_candidate",
        }

        self._ensure_mock_candidate_asset_file(primary_ref, mock_ref)

        return [primary_ref, mock_ref]

    def _ensure_mock_candidate_asset_file(
        self,
        primary_ref: Dict[str, Any],
        candidate_ref: Dict[str, Any],
    ) -> None:
        primary_relative_path = str(primary_ref.get("relative_path") or "").strip()
        candidate_relative_path = str(candidate_ref.get("relative_path") or "").strip()

        if not primary_relative_path or not candidate_relative_path:
            return

        source_path = PROJECT_ROOT / primary_relative_path
        target_path = PROJECT_ROOT / candidate_relative_path

        if not source_path.exists():
            return

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if not target_path.exists():
            shutil.copyfile(source_path, target_path)

    def _scene_index_by_id(
        self,
        scenes: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        for index, scene in enumerate(scenes, start=1):
            scene_id = str(scene.get("scene_id") or "").strip()
            if scene_id:
                mapping[scene_id] = index
        return mapping

    def _run_single_scene_api_image_asset(
        self,
        ctx: StepContext,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        prompt_by_scene_id, _ = self._image_prompt_item_maps(outputs)

        run_dir = self._ensure_image_run_dir(ctx.run_id)
        scene_id = str(scene.get("scene_id") or f"scene_{scene_index:02d}")
        prompt_item = prompt_by_scene_id.get(scene_id) or {}
        base_prompt = str(prompt_item.get("prompt") or "").strip()

        if not base_prompt:
            visual_description = str(scene.get("visual_description") or "").strip()
            narration = str(scene.get("narration") or "").strip()
            base_prompt = (
                visual_description or narration or f"storybook scene {scene_id}"
            )

        asset_meta = self._image_asset_metadata(
            scene=scene,
            prompt_item=prompt_item,
            fallback_scene_title=str(scene.get("scene_title") or "").strip(),
        )

        candidate_asset_refs: List[Dict[str, Any]] = []
        adapter = ApiImageGeneratorAdapter(self)

        for candidate_index, candidate_suffix in enumerate(
            ["candidate_a", "candidate_b"]
        ):
            candidate_scene = self._scene_candidate_variant(
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

            candidate_asset_refs.append(
                {
                    "scene_id": scene_id,
                    "file_name": file_name,
                    "relative_path": task.relative_path,
                    "public_url": task.public_url,
                    "mime_type": "image/png",
                    "provider": "api_image_generator",
                }
            )

        selection = select_best_candidate(
            candidate_asset_refs=candidate_asset_refs,
            prompt=base_prompt,
            characters=asset_meta["characters"],
        )
        candidate_asset_refs = selection["candidate_asset_refs"]
        selected_asset_ref = selection["selected_asset_ref"]

        return {
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
            "status": "generated",
            "candidate_asset_refs": candidate_asset_refs,
            "selection_source": selection.get("selection_source"),
            "selection_reason": selection.get("selection_reason"),
            "candidate_scores": selection.get("candidate_scores") or [],
        }

    def _run_single_scene_image_asset(
        self,
        ctx: StepContext,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
    ) -> Dict[str, Any]:
        return self._single_scene_image_support.run_single_scene_image_asset(
            ctx=ctx,
            outputs=outputs,
            scene=scene,
            scene_index=scene_index,
        )

    def _apply_manual_image_selection(
        self,
        image_review: Dict[str, Any],
        scene_id: str,
        selected_asset_ref: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated_review = dict(image_review or {})
        selected_assets = updated_review.get("selected_assets") or []

        normalized_scene_id = str(scene_id or "").strip()
        if not normalized_scene_id:
            raise ValueError("scene_id is required")

        if not isinstance(selected_asset_ref, dict) or not selected_asset_ref:
            raise ValueError("selected_asset_ref is required")

        updated_items: List[Dict[str, Any]] = []
        found = False

        for item in selected_assets:
            if not isinstance(item, dict):
                updated_items.append(item)
                continue

            item_scene_id = str(item.get("scene_id") or "").strip()
            if item_scene_id != normalized_scene_id:
                updated_items.append(item)
                continue

            updated_item = dict(item)
            updated_item["selected_asset_ref"] = dict(selected_asset_ref)
            updated_item["selection_source"] = "manual_selection"
            updated_item["selection_mode"] = "manual_click_override"
            updated_item["review_status"] = "manually_selected"
            updated_item["selection_reason"] = "selected_by_user_click"

            candidate_asset_refs = updated_item.get("candidate_asset_refs") or []
            if isinstance(candidate_asset_refs, list):
                already_exists = False
                for candidate in candidate_asset_refs:
                    if not isinstance(candidate, dict):
                        continue
                    if (
                        str(candidate.get("relative_path") or "").strip()
                        == str(selected_asset_ref.get("relative_path") or "").strip()
                        and str(candidate.get("file_name") or "").strip()
                        == str(selected_asset_ref.get("file_name") or "").strip()
                    ):
                        already_exists = True
                        break

                if not already_exists:
                    updated_item["candidate_asset_refs"] = candidate_asset_refs + [
                        dict(selected_asset_ref)
                    ]
            else:
                updated_item["candidate_asset_refs"] = [dict(selected_asset_ref)]

            updated_items.append(updated_item)
            found = True

        if not found:
            raise ValueError(
                f"scene_id not found in image_review: {normalized_scene_id}"
            )

        updated_review["selected_assets"] = updated_items
        updated_review["selected_count"] = len(
            [item for item in updated_items if isinstance(item, dict)]
        )
        updated_review["mode"] = "selection_contract"
        return updated_review

    def update_image_review_selection(
        self,
        workflow_id: str,
        session_id: Optional[str],
        run_id: str,
        scene_id: str,
        selected_asset_ref: Dict[str, Any],
        image_review: Dict[str, Any],
        storyboard: Dict[str, Any],
        workflow_input: Dict[str, Any],
        video_provider: str = "mock",
    ) -> Dict[str, Any]:
        updated_image_review = self._apply_manual_image_selection(
            image_review=image_review,
            scene_id=scene_id,
            selected_asset_ref=selected_asset_ref,
        )

        storyboard_scenes = (storyboard or {}).get("scenes") or []
        if not isinstance(storyboard_scenes, list) or not storyboard_scenes:
            raise ValueError("storyboard.scenes is required")

        try:
            normalized_input = WorkflowInput(
                **{
                    **(workflow_input or {}),
                    "video_provider": (
                        str(video_provider or "").strip()
                        or str(
                            (workflow_input or {}).get("video_provider") or ""
                        ).strip()
                        or "mock"
                    ),
                }
            )
        except Exception as e:
            raise ValueError(f"invalid workflow_input: {e}") from e

        ctx = StepContext(
            workflow_id=workflow_id,
            session_id=session_id,
            run_id=run_id,
            input=normalized_input,
        )

        image_assets = self.build_image_assets_from_selected_assets(
            run_id=run_id,
            image_review=updated_image_review,
            provider=str(self._image_provider_name()),
        )

        outputs = {
            "image_review": updated_image_review,
            "image_assets": image_assets,
            "storyboard": {
                "scenes": storyboard_scenes,
            },
        }

        video_prompts = self._video_prompts.build_video_provider_prompts(
            ctx=ctx,
            scenes=storyboard_scenes,
            outputs=outputs,
        )

        return {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "run_id": run_id,
            "scene_id": scene_id,
            "image_review": updated_image_review,
            "image_assets": image_assets,
            "video_prompts": video_prompts,
        }

    def refresh_image_review_scene(
        self,
        workflow_id: str,
        session_id: Optional[str],
        run_id: str,
        scene_id: str,
        storyboard: Dict[str, Any],
        workflow_input: Dict[str, Any],
        image_review: Dict[str, Any],
        character_manifest: Optional[Dict[str, Any]] = None,
        image_prompts: Optional[Dict[str, Any]] = None,
        video_provider: str = "mock",
    ) -> Dict[str, Any]:
        normalized_scene_id = str(scene_id or "").strip()
        if not normalized_scene_id:
            raise ValueError("scene_id is required")

        storyboard_scenes = (storyboard or {}).get("scenes") or []
        if not isinstance(storyboard_scenes, list) or not storyboard_scenes:
            raise ValueError("storyboard.scenes is required")

        scene_index_by_id = self._scene_index_by_id(storyboard_scenes)
        target_scene = None
        for item in storyboard_scenes:
            if str(item.get("scene_id") or "").strip() == normalized_scene_id:
                target_scene = item
                break

        if target_scene is None:
            raise ValueError(f"scene_id not found in storyboard: {normalized_scene_id}")

        try:
            normalized_input = WorkflowInput(
                **{
                    **(workflow_input or {}),
                    "video_provider": (
                        str(video_provider or "").strip()
                        or str(
                            (workflow_input or {}).get("video_provider") or ""
                        ).strip()
                        or "mock"
                    ),
                }
            )
        except Exception as e:
            raise ValueError(f"invalid workflow_input: {e}") from e

        ctx = StepContext(
            workflow_id=workflow_id,
            session_id=session_id,
            run_id=run_id,
            input=normalized_input,
        )

        run_context = self._session.get_run_context(run_id) or {}
        stored_character_manifest = (
            dict(character_manifest or {})
            or run_context.get("character_manifest")
            or {}
        )
        stored_image_prompts = (
            dict(image_prompts or {})
            or run_context.get("image_prompts")
            or {}
        )

        outputs: Dict[str, Any] = {
            "storyboard": {
                "scenes": storyboard_scenes,
            },
            "character_manifest": stored_character_manifest,
            "image_prompts": stored_image_prompts,
            "image_review": dict(image_review or {}),
        }

        single_scene_assets = self._run_single_scene_image_asset(
            ctx=ctx,
            outputs=outputs,
            scene=target_scene,
            scene_index=scene_index_by_id.get(normalized_scene_id, 1),
        )
        outputs["image_assets"] = single_scene_assets

        image_assets_status = (
            str(single_scene_assets.get("status") or "").strip().lower()
        )
        if image_assets_status in {"pending", "retrying"}:
            updated_image_review = dict(image_review or {})
            scene_review_item: Dict[str, Any] = {}
        else:
            provider = str(single_scene_assets.get("provider") or "").strip()
            assets = single_scene_assets.get("assets") or []
            first_asset = assets[0] if isinstance(assets, list) and assets else {}
            if not isinstance(first_asset, dict) or not first_asset:
                raise RuntimeError("single scene image asset is missing")
            scene_review_item = self._image_review.build_image_review_item_from_asset(
                first_asset,
                provider=provider,
            )
            updated_image_review = self._image_review.upsert_image_review_item(
                image_review=image_review,
                scene_review_item=scene_review_item,
                provider=provider,
            )

        outputs["image_review"] = updated_image_review

        outputs["image_assets"] = self.build_image_assets_from_selected_assets(
            run_id=run_id,
            image_review=updated_image_review,
            provider=str(
                single_scene_assets.get("provider") or self._image_provider_name()
            ),
        )

        video_prompts = self._run_video_prompts(ctx, outputs)

        return {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "run_id": run_id,
            "scene_id": normalized_scene_id,
            "scene_image_asset": single_scene_assets,
            "scene_review_item": (
                scene_review_item
                if image_assets_status not in {"pending", "retrying"}
                else {}
            ),
            "image_assets": outputs["image_assets"],
            "image_review": updated_image_review,
            "video_prompts": video_prompts,
        }

    def refresh_image_review(
        self,
        workflow_id: str,
        session_id: Optional[str],
        run_id: str,
        storyboard: Dict[str, Any],
        workflow_input: Dict[str, Any],
        image_review: Dict[str, Any],
        video_provider: str = "mock",
    ) -> Dict[str, Any]:
        normalized_run_id = str(run_id or "").strip()
        if not normalized_run_id:
            raise ValueError("run_id is required")

        stored_context = self._session.get_run_context(normalized_run_id) or {}

        resolved_workflow_id = (
            str(workflow_id or "").strip()
            or str(stored_context.get("workflow_id") or "").strip()
        )
        if not resolved_workflow_id:
            raise ValueError("workflow_id is required")

        resolved_session_id = session_id
        if resolved_session_id is None:
            stored_session_id = stored_context.get("session_id")
            if isinstance(stored_session_id, str) and stored_session_id.strip():
                resolved_session_id = stored_session_id.strip()

        resolved_storyboard = storyboard or stored_context.get("storyboard") or {}
        storyboard_scenes = (resolved_storyboard or {}).get("scenes") or []
        if not isinstance(storyboard_scenes, list) or not storyboard_scenes:
            raise ValueError("storyboard.scenes is required")

        stored_workflow_input = stored_context.get("workflow_input") or {}
        merged_workflow_input = {
            **stored_workflow_input,
            **(workflow_input or {}),
        }

        try:
            normalized_input = WorkflowInput(
                **{
                    **merged_workflow_input,
                    "video_provider": (
                        str(video_provider or "").strip()
                        or str(
                            merged_workflow_input.get("video_provider") or ""
                        ).strip()
                        or "mock"
                    ),
                }
            )
        except Exception as e:
            raise ValueError(f"invalid workflow_input: {e}") from e

        ctx = StepContext(
            workflow_id=resolved_workflow_id,
            session_id=resolved_session_id,
            run_id=normalized_run_id,
            input=normalized_input,
        )

        outputs: Dict[str, Any] = {
            "storyboard": {
                "scenes": storyboard_scenes,
            },
        }

        stored_sentence_shots = stored_context.get("sentence_shots") or {}
        if stored_sentence_shots:
            outputs["sentence_shots"] = stored_sentence_shots

        stored_image_prompts = stored_context.get("image_prompts") or {}
        if stored_image_prompts:
            outputs["image_prompts"] = stored_image_prompts

        previous_image_review = image_review or stored_context.get("image_review") or {}
        if previous_image_review:
            outputs["image_review"] = previous_image_review

        image_assets = self._run_image_assets(ctx, outputs)
        outputs["image_assets"] = image_assets

        image_assets_status = str(image_assets.get("status") or "").strip().lower()
        if image_assets_status in {"pending", "retrying"}:
            updated_image_review = self._image_review.build_pending_image_review(
                reason="waiting_for_image_assets"
            )
        else:
            updated_image_review = self._image_review.build_default_image_review(image_assets)

        outputs["image_review"] = updated_image_review
        video_prompts = self._run_video_prompts(ctx, outputs)
        outputs["video_prompts"] = video_prompts

        self._session.save_run_context(
            workflow_id=resolved_workflow_id,
            session_id=resolved_session_id,
            run_id=normalized_run_id,
            outputs=outputs,
            workflow_input=normalized_input.model_dump(),
        )

        return {
            "workflow_id": resolved_workflow_id,
            "session_id": resolved_session_id,
            "run_id": normalized_run_id,
            "image_assets": image_assets,
            "image_review": updated_image_review,
            "video_prompts": video_prompts,
        }

    def _run_story(self, ctx: StepContext, outputs: Dict[str, Any]) -> Dict[str, Any]:
        return self._story_support.run_story(ctx, outputs)

    def _run_storyboard(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self._storyboard.run_storyboard(ctx, outputs)

    def _split_story_for_scenes(self, text: str, scene_count: int) -> List[str]:
        return self._storyboard.split_story_for_scenes(text, scene_count)

    def _split_text_by_char_balance(self, text: str, scene_count: int) -> List[str]:
        return self._storyboard.split_text_by_char_balance(text, scene_count)

    def _dedupe_adjacent_text(self, items: List[str]) -> List[str]:
        return self._storyboard.dedupe_adjacent_text(items)

    def _run_sentence_shots(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self._storyboard.run_sentence_shots(ctx, outputs)

    def _split_story_sentences(self, text: str) -> List[str]:
        return self._storyboard.split_story_sentences(text)

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

    def _build_scene_png(
        self,
        ctx: StepContext,
        scene: Dict[str, Any],
        index: int,
    ) -> bytes:
        from io import BytesIO
        from PIL import Image

        ppm_bytes = self._build_scene_ppm(ctx, scene, index)

        input_buffer = BytesIO(ppm_bytes)
        output_buffer = BytesIO()

        image = Image.open(input_buffer)
        image.save(output_buffer, format="PNG")

        return output_buffer.getvalue()

    def _image_prompt_item_maps(
        self, outputs: Dict[str, Any]
    ) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        image_prompts = outputs.get("image_prompts") or {}
        prompt_items = image_prompts.get("prompts") or []

        prompt_by_scene_id: Dict[str, Dict[str, Any]] = {}
        prompt_by_shot_id: Dict[str, Dict[str, Any]] = {}

        for item in prompt_items:
            if not isinstance(item, dict):
                continue

            scene_id = str(item.get("scene_id") or "").strip()
            shot_id = str(item.get("shot_id") or "").strip()

            if scene_id:
                prompt_by_scene_id[scene_id] = item
            if shot_id:
                prompt_by_shot_id[shot_id] = item

        return prompt_by_scene_id, prompt_by_shot_id

    def _image_asset_metadata(
        self,
        *,
        scene: Optional[Dict[str, Any]] = None,
        prompt_item: Optional[Dict[str, Any]] = None,
        fallback_scene_title: str = "",
    ) -> Dict[str, Any]:
        scene = scene or {}
        prompt_item = prompt_item or {}

        scene_title = str(
            prompt_item.get("scene_title")
            or scene.get("scene_title")
            or fallback_scene_title
            or ""
        ).strip()

        characters = prompt_item.get("characters")
        if not isinstance(characters, list):
            characters = scene.get("characters") or []
        if not isinstance(characters, list):
            characters = []

        prompt_text = str(prompt_item.get("prompt") or "").strip()

        return {
            "scene_title": scene_title,
            "characters": characters,
            "character_ids": self._scene_characters.character_ids_from_bindings(
                characters
            ),
            "prompt": prompt_text,
        }

    def _scene_candidate_variant(
        self,
        *,
        scene: Dict[str, Any],
        candidate_index: int,
    ) -> Dict[str, Any]:
        variant = dict(scene)

        scene_title = str(scene.get("scene_title") or "").strip()
        visual_description = str(scene.get("visual_description") or "").strip()
        narration = str(scene.get("narration") or "").strip()
        shot_type = str(scene.get("shot_type") or "medium").strip()

        if candidate_index == 0:
            variant["candidate_key"] = "candidate_a"
            variant["candidate_label"] = "Primary Composition"
            return variant

        variant["candidate_key"] = "candidate_b"
        variant["candidate_label"] = "Alternate Composition"

        if shot_type == "wide":
            variant["shot_type"] = "medium"
        elif shot_type == "medium":
            variant["shot_type"] = "close"
        else:
            variant["shot_type"] = "wide"

        if scene_title:
            variant["scene_title"] = f"{scene_title} Alt"

        if visual_description:
            variant["visual_description"] = (
                f"{visual_description}; alternate composition, different framing, "
                "slightly changed pose emphasis, secondary visual arrangement"
            )

        if narration:
            variant["narration"] = narration

        return variant

    def _run_image_assets(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        queue = ImageProviderQueue(self)
        return queue.run(ctx=ctx, outputs=outputs)

    def _run_video_prompts(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        image_assets = outputs.get("image_assets") or {}
        image_assets_status = str(image_assets.get("status") or "").strip().lower()

        if image_assets_status in {"pending", "retrying"}:
            return {
                "provider": self._normalized_video_provider(ctx.input.video_provider),
                "status": "pending",
                "reason": "waiting_for_image_assets",
                "prompts": [],
            }

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        return self._video_prompts.build_video_provider_prompts(ctx, scenes, outputs)

    def _run_render_plan(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        subtitles = outputs.get("subtitles") or {}
        subtitles_enabled = bool(subtitles.get("enabled"))

        return self._render_plan.build_render_plan_by_provider(ctx, scenes, subtitles_enabled)
