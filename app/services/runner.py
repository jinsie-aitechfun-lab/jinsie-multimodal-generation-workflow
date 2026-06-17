from __future__ import annotations

import http.client
import json
import ast
import re
import os
import socket
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
from app.services.runner_character_labels import RunnerCharacterLabelsSupport
from app.services.runner_character_manifest import RunnerCharacterManifestSupport
from app.services.cancellation import is_cancelled as _is_cancelled
from app.services.runner_errors import (
    UnknownStepError,
    UnknownVideoProviderError,
    WorkflowCancelledError,
)
from app.services.runner_image_asset_refs import RunnerImageAssetRefsSupport
from app.services.runner_image_prompts_support import RunnerImagePromptsSupport
from app.services.runner_image_review import RunnerImageReviewSupport
from app.services.runner_image_selection_support import RunnerImageSelectionSupport
from app.services.runner_render_plan import RunnerRenderPlanSupport
from app.services.runner_scene_blueprints import RunnerSceneBlueprintsSupport
from app.services.runner_scene_characters import RunnerSceneCharactersSupport
from app.services.runner_scene_render_fallback import RunnerSceneRenderFallbackSupport
from app.services.runner_scene_render_storybook import RunnerSceneRenderStorybookSupport
from app.services.runner_session import RunnerSessionStore
from app.services.runner_story_support import RunnerStorySupport
from app.services.runner_story_text import RunnerStoryTextSupport
from app.services.runner_storyboard import RunnerStoryboardSupport
from app.services.runner_video_prompts import RunnerVideoPromptsSupport
from app.services.runner_voice_support import RunnerVoiceSupport
from app.services.image_provider_queue import ImageProviderQueue
from app.services.runner_single_scene_image_support import RunnerSingleSceneImageSupport
from app.services.topic_character_infer import infer_primary_character_manifest
from app.services.story_subject_extractor import extract_story_subjects
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

    def _run_async(
        self,
        run_input: dict,
        callback: callable,
        error_callback: Optional[callable] = None,
        progress_callback: Optional[callable] = None,
    ):
        import threading
        import traceback
        from app.schemas.workflow import WorkflowRunRequest

        def _task():
            try:
                request = WorkflowRunRequest(**run_input)
                result = self.run(request, progress_callback=progress_callback)
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
                if error_callback is not None:
                    error_callback(error)

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
        self._character_labels = RunnerCharacterLabelsSupport(self)
        self._character_manifest_support = RunnerCharacterManifestSupport(self)
        self._image_asset_refs = RunnerImageAssetRefsSupport(self)
        self._image_prompts = RunnerImagePromptsSupport(self)
        self._image_selection_support = RunnerImageSelectionSupport(self)
        self._image_review = RunnerImageReviewSupport(self)
        self._render_plan = RunnerRenderPlanSupport(self)
        self._scene_blueprints_support = RunnerSceneBlueprintsSupport(self)
        self._scene_characters = RunnerSceneCharactersSupport(self)
        self._scene_render_fallback = RunnerSceneRenderFallbackSupport(self)
        self._scene_render_storybook = RunnerSceneRenderStorybookSupport(self)
        self._single_scene_image_support = RunnerSingleSceneImageSupport(self)
        self._story_support = RunnerStorySupport(self)
        self._story_text = RunnerStoryTextSupport(self)
        self._storyboard = RunnerStoryboardSupport(self)
        self._video_prompts = RunnerVideoPromptsSupport(self)
        self._voice_support = RunnerVoiceSupport(self)

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

    def _llm_fallback_api_base_url(self) -> str:
        return (os.getenv("LLM_FALLBACK_BASE_URL") or "").strip().rstrip("/")

    def _llm_fallback_api_key(self) -> str:
        return (os.getenv("LLM_FALLBACK_API_KEY") or "").strip()

    def _llm_fallback_model_name(self) -> str:
        return (
            (os.getenv("LLM_FALLBACK_MODEL") or "").strip()
            or self._story_model_name()
        )

    # Transient network failures that warrant a quick retry rather than a
    # straight fall-through to template generation. Listed at class level
    # so it's discoverable from one place.
    _LLM_RETRYABLE_ERRORS = (
        http.client.RemoteDisconnected,
        http.client.IncompleteRead,
        ConnectionError,           # ConnectionResetError, ConnectionAbortedError, etc.
        socket.timeout,
        TimeoutError,
    )
    _LLM_RETRY_BACKOFF_SECONDS = (0.8, 2.0)  # 3 attempts total: 0, 0.8s, 2.0s

    def _call_llm_chat(
        self,
        *,
        api_base_url: str,
        api_key: str,
        payload: Dict[str, Any],
        timeout: int,
        workflow_id: Optional[str] = None,
    ) -> str:
        """Send one OpenAI-compatible chat/completions request; return raw content string.

        Retries up to 3 times on transient network errors (RemoteDisconnected,
        connection resets, timeouts, HTTP 5xx). 4xx errors and empty responses
        are not retried — they indicate a real problem, not a transient blip.

        If ``workflow_id`` is provided, the retry loop checks the cancellation
        registry between attempts and raises ``WorkflowCancelledError`` as soon
        as the user has requested cancel. This shortens worst-case cancel
        latency from ~3×timeout to ~1×timeout for any step that hits this
        method.
        """
        url = f"{api_base_url.rstrip('/')}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        def _raise_if_cancelled() -> None:
            if workflow_id and _is_cancelled(workflow_id):
                raise WorkflowCancelledError(workflow_id, partial_outputs={})

        last_err: Optional[BaseException] = None
        # The first attempt has zero wait; subsequent attempts back off.
        # Cancellation is observed before every attempt (including the first,
        # for the case where cancel arrived between step boundary and the
        # call site) and during the backoff sleep so the user doesn't wait
        # for a full timeout when they've already asked to stop.
        for attempt_index in range(len(self._LLM_RETRY_BACKOFF_SECONDS) + 1):
            _raise_if_cancelled()
            if attempt_index > 0:
                # Sleep in small slices so cancel responds within ~0.2s
                # rather than the full backoff duration.
                backoff = self._LLM_RETRY_BACKOFF_SECONDS[attempt_index - 1]
                slept = 0.0
                while slept < backoff:
                    time.sleep(min(0.2, backoff - slept))
                    slept += 0.2
                    _raise_if_cancelled()
            try:
                req = urllib_request.Request(
                    url=url,
                    data=body,
                    headers=headers,
                    method="POST",
                )
                with urllib_request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                if not raw:
                    raise RuntimeError("LLM response is empty")
                data = json.loads(raw.decode("utf-8", errors="ignore"))
                content = (
                    (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
                ).strip()
                if not content:
                    raise RuntimeError("LLM content is empty")
                return content
            except urllib_error.HTTPError as e:
                # Only retry 5xx server errors. 4xx is a client mistake
                # (bad key, malformed payload, quota exhausted) — retrying
                # won't change the outcome.
                if 500 <= e.code < 600:
                    last_err = e
                    _raise_if_cancelled()
                    continue
                raise
            except self._LLM_RETRYABLE_ERRORS as e:
                last_err = e
                _raise_if_cancelled()
                continue
            except urllib_error.URLError as e:
                # URLError wraps lower-level network errors. Most are
                # transient (DNS, refused, reset); retry them. The
                # underlying reason is in e.reason — non-network reasons
                # (e.g. unknown URL scheme) are rare and still safe to
                # retry because they'd reproduce, not hang.
                last_err = e
                _raise_if_cancelled()
                continue

        # All attempts exhausted — surface the last exception so callers
        # can decide whether to fall back to template or fail outright.
        if last_err is not None:
            raise last_err
        # Defensive — loop always either returns or sets last_err, but
        # raising a generic error here keeps the type checker happy.
        raise RuntimeError("LLM call failed after retries (no exception recorded)")

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
    ) -> Dict[str, Any]:
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
            f"Narration pacing target only: about {story_plan['duration_sec']} seconds. Do not mention this duration in the story.\n"
            f"Target Chinese story length: {story_plan['target_min_chars']}-{story_plan['target_max_chars']} Chinese characters, about {story_plan['target_chars']} Chinese characters.\n"
            f"Expected narration: enough complete narration for about {story_plan['duration_sec']} seconds and {story_plan['scene_count']} scenes.\n"
            f"Constraints:\n"
            f"- The plot must meaningfully reflect the topic (not a generic template).\n"
            f"- Generate enough story content for the selected duration.\n"
            f"- Provide a complete structure: beginning, development, problem or discovery, action, and a concrete story-specific resolution.\n"
            f"- The ending must describe what SPECIFICALLY happens at the end of THIS story — a concrete action, reunion, achievement, or moment unique to the characters and topic.\n"
            f"- Do NOT use generic warmth formulas such as '心里暖暖的', '收获了勇气和成长', '明白了XX的道理', '带来美好的收获', or any variation of those phrases.\n"
            f"- Do not repeat sentences or adjacent ideas.\n"
            f"- Do not include scene numbers, bullet points, markdown, JSON, or section headings.\n"
            f"- Do not include the selected duration, seconds, target length, or phrases such as 60秒 / 有6秒 in the story.\n"
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
            "temperature": 0.95,
            "max_tokens": 1400,
        }

        timeout = self._story_timeout_seconds()
        provider_used = "primary"
        fallback_reason: Optional[str] = None

        try:
            content = self._call_llm_chat(
                api_base_url=self._llm_api_base_url(),
                api_key=api_key,
                payload=payload,
                timeout=timeout,
                workflow_id=ctx.workflow_id,
            )
        except WorkflowCancelledError:
            # User-requested cancel must propagate, not fall back to the
            # secondary provider. The runner's step boundary will catch it.
            raise
        except Exception as primary_err:
            fallback_url = self._llm_fallback_api_base_url()
            fallback_key = self._llm_fallback_api_key()
            if not fallback_url or not fallback_key:
                raise

            fallback_model = self._llm_fallback_model_name()
            fallback_payload = dict(payload)
            fallback_payload["model"] = fallback_model

            content = self._call_llm_chat(
                api_base_url=fallback_url,
                api_key=fallback_key,
                payload=fallback_payload,
                timeout=timeout,
                workflow_id=ctx.workflow_id,
            )
            provider_used = "fallback"
            fallback_reason = f"{type(primary_err).__name__}: {primary_err}"

        title = f"{topic}的故事"
        summary = f"一个围绕“{topic}”展开的短篇故事，整体气质{tone_label}，适合做成{audience_label}向内容。"

        parsed = parse_story_payload(content, topic=topic)
        text = parsed["text"] if parsed and parsed.get("text") else content

        result: Dict[str, Any] = {
            "title": title.strip(),
            "summary": summary.strip(),
            "text": text.strip(),
            "provider_used": provider_used,
        }
        if fallback_reason:
            result["fallback_reason"] = fallback_reason
        return result

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
        # Priority order:
        #   1) TTS_VOICE_STYLE_<style>  — the voice the USER explicitly
        #      picked in the UI. This must win over speaker-defaults so
        #      that switching "旁白配音" between 温暖男声 / 温柔女声
        #      actually changes the rendered TTS voice.
        #   2) TTS_VOICE_<speaker>      — speaker-default fallback, only
        #      used when no style is provided (or the style key isn't
        #      configured in .env).
        #   3) TTS_VOICE                 — global default.
        #
        # Previous order put speaker-default FIRST, which meant
        # TTS_VOICE_NARRATOR (typically a single fixed voice in .env)
        # silently overrode every voice_style the user picked in single
        # mode — they always got the narrator default regardless of UI
        # selection. The bug was: select 温暖男声 → still hear claire
        # (female narrator default).
        style_key = voice_style.strip().upper()
        style_specific = os.getenv(f"TTS_VOICE_STYLE_{style_key}", "").strip()
        if style_specific:
            return style_specific

        speaker_key = speaker.strip().upper()
        speaker_specific = os.getenv(f"TTS_VOICE_{speaker_key}", "").strip()
        if speaker_specific:
            return speaker_specific

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
        speed: Optional[float] = None,
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
        if speed is not None:
            payload["speed"] = round(max(0.25, min(4.0, float(speed))), 2)

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

    def run(
        self,
        req: WorkflowRunRequest,
        progress_callback: Optional[callable] = None,
    ) -> WorkflowRunResponse:
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

        total_steps = len(req.steps)

        def emit_progress(
            *,
            current_step: str,
            current_step_index: int,
            completed_steps: int,
        ) -> None:
            if progress_callback is None:
                return

            try:
                progress_callback(
                    {
                        "current_step": current_step,
                        "current_step_index": current_step_index,
                        "completed_steps": completed_steps,
                        "total_steps": total_steps,
                        "progress_percent": (
                            round((completed_steps / total_steps) * 100)
                            if total_steps
                            else 0
                        ),
                    }
                )
            except Exception as error:
                print(f"[WorkflowRunner] progress callback failed: {error}")

        def _check_cancelled():
            """Raise WorkflowCancelledError if the user has requested a
            cancel. Best-effort persists partial outputs first so the
            client can still see what was produced before the stop."""
            if not _is_cancelled(req.workflow_id):
                return
            try:
                out_dir = PROJECT_ROOT / "assets" / "mock" / str(req.workflow_id)
                out_dir.mkdir(parents=True, exist_ok=True)
                with open(out_dir / "outputs.json", "w", encoding="utf-8") as f:
                    json.dump(aggregated_outputs, f, ensure_ascii=False, indent=2, default=str)
            except Exception as error:  # noqa: BLE001
                print(f"[WorkflowRunner] partial-output save on cancel failed: {error}")
            raise WorkflowCancelledError(req.workflow_id, partial_outputs=aggregated_outputs)

        for step_index, step in enumerate(req.steps, start=1):
            _check_cancelled()

            name = step.name.strip()
            handler = self._handlers.get(name)
            if handler is None:
                raise UnknownStepError(f"Unknown step: {name}")

            emit_progress(
                current_step=name,
                current_step_index=step_index,
                completed_steps=step_index - 1,
            )

            if name == "image_assets":
                output = self._image_review.build_deferred_image_assets_output(ctx)
            else:
                output = handler(ctx, aggregated_outputs)

            _check_cancelled()

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
        return self._image_prompts.run_image_prompts(ctx, outputs)

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
        return self._voice_support.normalized_voice_mode(voice_mode)

    def _speaker_profiles(self, ctx: StepContext) -> Dict[str, str]:
        return self._voice_support.speaker_profiles(ctx)

    def _character_speaker_profiles(self, ctx: StepContext) -> Dict[str, str]:
        return self._voice_support.character_speaker_profiles(ctx)

    def _character_speaker_name(self, ctx: StepContext) -> str:
        return self._voice_support.character_speaker_name(ctx)

    def _secondary_character_speaker_name(self, ctx: StepContext) -> str:
        return self._voice_support.secondary_character_speaker_name(ctx)

    def _detect_character_speaker(self, ctx: StepContext, text: str) -> str:
        return self._voice_support.detect_character_speaker(ctx, text)

    def _resolve_character_speaker(self, ctx: StepContext, text: str) -> Dict[str, str]:
        return self._voice_support.resolve_character_speaker(ctx, text)

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
        return self._voice_support.build_dialogue_line(
            line_id=line_id,
            text=text,
            scene_id=scene_id,
            shot_id=shot_id,
            speaker=speaker,
            voice_style=voice_style,
        )

    def _clean_story_topic(self, topic: str) -> str:
        return self._character_labels.clean_story_topic(topic)

    def _topic_primary_character_display_label(self, ctx: StepContext) -> str:
        return self._character_labels.topic_primary_character_display_label(ctx)

    def _main_character_display_label(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self._character_labels.main_character_display_label(ctx, outputs)

    def _secondary_character_display_label(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self._character_labels.secondary_character_display_label(ctx, outputs)

    def _has_secondary_character(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self._character_labels.has_secondary_character(ctx, outputs)

    def _main_character_label(self, ctx: StepContext) -> str:
        return self._character_labels.main_character_label(ctx)

    def _main_character_subject(self, ctx: StepContext) -> str:
        return self._character_labels.main_character_subject(ctx)

    def _visual_subject_constraints(self, subject: str) -> str:
        return self._character_labels.visual_subject_constraints(subject)

    def _character_consistency_anchor(
        self,
        ctx: StepContext,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self._character_labels.character_consistency_anchor(ctx, outputs)

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
        return self._scene_blueprints_support.expand_scene_blueprints(
            base, scene_count
        )

    def _scene_blueprints(
        self,
        ctx: StepContext,
        scene_count: int,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        return self._scene_blueprints_support.scene_blueprints(
            ctx, scene_count, outputs
        )

    def _image_asset_by_scene_id(
        self, outputs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        return self._image_asset_refs.image_asset_by_scene_id(outputs)

    def _image_asset_ref_from_item(
        self,
        item: Dict[str, Any],
        provider: str,
    ) -> Dict[str, Any]:
        return self._image_asset_refs.image_asset_ref_from_item(item, provider)

    def _build_mock_candidate_asset_refs(
        self,
        item: Dict[str, Any],
        provider: str,
    ) -> List[Dict[str, Any]]:
        return self._image_asset_refs.build_mock_candidate_asset_refs(item, provider)

    def _ensure_mock_candidate_asset_file(
        self,
        primary_ref: Dict[str, Any],
        candidate_ref: Dict[str, Any],
    ) -> None:
        self._image_asset_refs.ensure_mock_candidate_asset_file(
            primary_ref, candidate_ref
        )

    def _scene_index_by_id(
        self,
        scenes: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        return self._image_asset_refs.scene_index_by_id(scenes)

    def _run_single_scene_api_image_asset(
        self,
        ctx: StepContext,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
    ) -> Dict[str, Any]:
        return self._single_scene_image_support.run_single_scene_api_image_asset(
            ctx=ctx,
            outputs=outputs,
            scene=scene,
            scene_index=scene_index,
        )

    def _run_single_scene_image_asset(
        self,
        ctx: StepContext,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
        scene_index: int,
        preserve_seed: bool = False,
    ) -> Dict[str, Any]:
        return self._single_scene_image_support.run_single_scene_image_asset(
            ctx=ctx,
            outputs=outputs,
            scene=scene,
            scene_index=scene_index,
            preserve_seed=preserve_seed,
        )

    def _apply_manual_image_selection(
        self,
        image_review: Dict[str, Any],
        scene_id: str,
        selected_asset_ref: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._image_review.apply_manual_image_selection(
            image_review=image_review,
            scene_id=scene_id,
            selected_asset_ref=selected_asset_ref,
        )

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
        return self._image_review.update_image_review_selection(
            workflow_id=workflow_id,
            session_id=session_id,
            run_id=run_id,
            scene_id=scene_id,
            selected_asset_ref=selected_asset_ref,
            image_review=image_review,
            storyboard=storyboard,
            workflow_input=workflow_input,
            video_provider=video_provider,
        )

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
        preserve_seed: bool = False,
    ) -> Dict[str, Any]:
        return self._image_review.refresh_image_review_scene(
            workflow_id=workflow_id,
            session_id=session_id,
            run_id=run_id,
            scene_id=scene_id,
            storyboard=storyboard,
            workflow_input=workflow_input,
            image_review=image_review,
            character_manifest=character_manifest,
            image_prompts=image_prompts,
            video_provider=video_provider,
            preserve_seed=preserve_seed,
        )

    def refresh_image_review(
        self,
        workflow_id: str,
        session_id: Optional[str],
        run_id: str,
        storyboard: Dict[str, Any],
        workflow_input: Dict[str, Any],
        image_review: Dict[str, Any],
        character_manifest: Optional[Dict[str, Any]] = None,
        image_prompts: Optional[Any] = None,
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

        explicit_character_manifest = (
            dict(character_manifest)
            if isinstance(character_manifest, dict) and character_manifest
            else {}
        )
        stored_character_manifest = stored_context.get("character_manifest") or {}
        resolved_character_manifest = (
            explicit_character_manifest or stored_character_manifest
        )
        if resolved_character_manifest:
            outputs["character_manifest"] = resolved_character_manifest

        explicit_image_prompts = self._normalize_image_prompts_payload(image_prompts)
        stored_image_prompts = stored_context.get("image_prompts") or {}
        resolved_image_prompts = explicit_image_prompts or stored_image_prompts
        if resolved_image_prompts:
            outputs["image_prompts"] = resolved_image_prompts

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

    @staticmethod
    def _normalize_image_prompts_payload(image_prompts: Any) -> Dict[str, Any]:
        if isinstance(image_prompts, dict):
            return dict(image_prompts)
        if isinstance(image_prompts, list):
            return {"prompts": list(image_prompts)}
        return {}

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
        return self._scene_render_storybook.build_scene_ppm(ctx, scene, index)

    def _build_scene_png(
        self,
        ctx: StepContext,
        scene: Dict[str, Any],
        index: int,
    ) -> bytes:
        return self._scene_render_storybook.build_scene_png(ctx, scene, index)

    def _image_prompt_item_maps(
        self, outputs: Dict[str, Any]
    ) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        return self._image_asset_refs.image_prompt_item_maps(outputs)

    def _image_asset_metadata(
        self,
        *,
        scene: Optional[Dict[str, Any]] = None,
        prompt_item: Optional[Dict[str, Any]] = None,
        fallback_scene_title: str = "",
    ) -> Dict[str, Any]:
        return self._image_asset_refs.image_asset_metadata(
            scene=scene,
            prompt_item=prompt_item,
            fallback_scene_title=fallback_scene_title,
        )

    def _scene_candidate_variant(
        self,
        *,
        scene: Dict[str, Any],
        candidate_index: int,
    ) -> Dict[str, Any]:
        return self._image_asset_refs.scene_candidate_variant(
            scene=scene,
            candidate_index=candidate_index,
        )

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
