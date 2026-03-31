from __future__ import annotations

import json
import os
import subprocess
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
            str(sample.get("scene_id"))
            for sample in samples
            if sample.get("scene_id")
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
            int(stats.get("sample_count", 0))
            for stats in provider_stats.values()
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

        try:
            with urllib_request.urlopen(req, timeout=self._tts_timeout_seconds()) as resp:
                data = resp.read()
        except urllib_error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"TTS http error: status={e.code}, detail={detail}"
            ) from e
        except urllib_error.URLError as e:
            raise RuntimeError(f"TTS request failed: {e.reason}") from e

        output_path.write_bytes(data)

        return {
            "provider": self._tts_provider_name(),
            "model": model,
            "voice": voice,
            "output_bytes": len(data),
        }

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

    def _normalized_video_provider(self, provider: str) -> str:
        value = provider.strip().lower()
        if not value:
            return "mock"
        return value

    def _normalized_voice_mode(self, voice_mode: str) -> str:
        value = voice_mode.strip().lower()
        if value in {"single", "multi"}:
            return value
        return "single"

    def _speaker_profiles(self, ctx: StepContext) -> Dict[str, str]:
        profiles = dict(ctx.input.speaker_profiles or {})
        return {
            "narrator": profiles.get("narrator", ctx.input.voice_style),
            "mother": profiles.get("mother", "warm_female"),
            "child": profiles.get("child", "gentle_child"),
        }

    def _build_story_paragraphs(self, ctx: StepContext) -> List[str]:
        topic = ctx.input.topic.strip() or "一个温暖的童话故事"
        audience_label = self._audience_label(ctx.input.audience)
        tone_label = self._tone_label(ctx.input.tone)
        visual_label = self._visual_style_label(ctx.input.visual_style)
        character_label = self._character_style_label(ctx.input.character_style)

        paragraph_1 = (
            f"在一个安静又明亮的清晨，围绕“{topic}”展开了一段{tone_label}的小故事。"
            f"故事的主角是一位可爱的{character_label}朋友，它带着好奇心走进了新的旅程。"
        )
        paragraph_2 = (
            f"起初，一切都很顺利，可没过多久，主角就遇到了一点小麻烦。"
            f"它有些紧张，也有些犹豫，不知道该不该继续往前走。"
        )
        paragraph_3 = (
            f"但在一路上的观察、尝试和他人的帮助下，主角慢慢鼓起勇气，"
            f"一点点找到了解决问题的方法，也学会了相信自己。"
        )
        paragraph_4 = (
            f"最后，主角顺利完成了这段旅程，也收获了陪伴、勇气和成长。"
            f"这是一个适合{audience_label}观看、适合用{visual_label}风格呈现的{tone_label}故事。"
        )

        return [paragraph_1, paragraph_2, paragraph_3, paragraph_4]

    def _scene_blueprints(
        self, ctx: StepContext, scene_count: int
    ) -> List[Dict[str, str]]:
        tone_label = self._tone_label(ctx.input.tone)
        visual_label = self._visual_style_label(ctx.input.visual_style)
        character_label = self._character_style_label(ctx.input.character_style)

        base = [
            {
                "scene_title": "故事开场",
                "visual_description": (
                    f"{visual_label}风格画面，晨光柔和，{character_label}主角第一次出场，"
                    f"整体氛围{tone_label}、轻盈而有期待感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "遇到问题",
                "visual_description": (
                    f"{visual_label}风格画面，主角停下脚步思考，周围环境出现小小变化，"
                    f"画面强调困惑与转折。"
                ),
                "shot_type": "medium",
                "transition": "cut",
            },
            {
                "scene_title": "行动推进",
                "visual_description": (
                    f"{visual_label}风格画面，主角主动尝试解决问题，动作更明确，"
                    f"节奏变得积极，画面更有前进感。"
                ),
                "shot_type": "medium",
                "transition": "dissolve",
            },
            {
                "scene_title": "温暖收束",
                "visual_description": (
                    f"{visual_label}风格画面，主角完成旅程，表情放松，"
                    f"画面回到温暖明亮的氛围，用来承接结尾情绪。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
            {
                "scene_title": "回味结尾",
                "visual_description": (
                    f"{visual_label}风格画面，主角回头望向来时的路，"
                    f"环境安静舒展，用于强化余韵与成长感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "片尾定格",
                "visual_description": (
                    f"{visual_label}风格画面，主角站在新的起点上，"
                    f"适合作为片尾定格镜头，氛围柔和完整。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
        ]
        return base[:scene_count]

    def _build_video_prompt_base(
        self, ctx: StepContext, scene: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "scene_id": scene.get("scene_id"),
            "scene_title": scene.get("scene_title"),
            "visual_description": str(scene.get("visual_description", "")),
            "narration": str(scene.get("narration", "")),
            "duration_sec": scene.get("duration_sec"),
            "shot_type": scene.get("shot_type"),
            "transition": scene.get("transition"),
            "visual_style": ctx.input.visual_style,
            "tone": ctx.input.tone,
            "character_style": ctx.input.character_style,
            "provider": self._normalized_video_provider(ctx.input.video_provider),
        }

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
        for scene in scenes:
            base = self._build_video_prompt_base(ctx, scene)
            prompt = (
                f"Create a short animated video shot in {ctx.input.visual_style} style, "
                f"{ctx.input.tone} atmosphere, with {ctx.input.character_style} characters. "
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
        for scene in scenes:
            base = self._build_video_prompt_base(ctx, scene)
            prompts.append(
                {
                    "scene_id": base["scene_id"],
                    "scene_title": base["scene_title"],
                    "provider": "kling",
                    "prompt": (
                        f"[KLING] style={ctx.input.visual_style}; tone={ctx.input.tone}; "
                        f"character={ctx.input.character_style}; shot={base['shot_type']}; "
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
        for scene in scenes:
            base = self._build_video_prompt_base(ctx, scene)
            prompts.append(
                {
                    "scene_id": base["scene_id"],
                    "scene_title": base["scene_title"],
                    "provider": "jimeng",
                    "prompt": (
                        f"[JIMENG] visual={ctx.input.visual_style}; atmosphere={ctx.input.tone}; "
                        f"role={ctx.input.character_style}; transition={base['transition']}; "
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

    def _run_image_prompts(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        prompts: List[Dict[str, Any]] = []
        for scene in scenes:
            narration = str(scene.get("narration", ""))
            visual_description = str(scene.get("visual_description", ""))
            prompt = (
                f"{ctx.input.visual_style} illustration, {ctx.input.tone} mood, "
                f"{ctx.input.character_style} protagonist, {visual_description}, "
                f"story scene based on: {narration}"
            )
            prompts.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "prompt": prompt,
                }
            )

        return {"provider": "image_prompt_builder", "prompts": prompts}

    def _build_scene_ppm(self, ctx: StepContext, scene: Dict[str, Any], index: int) -> bytes:
        width = 1280
        height = 720

        # 简单渐变背景
        top = (247, 236, 255)
        bottom = (255, 249, 239)

        data = bytearray()
        header = f"P6\n{width} {height}\n255\n".encode("ascii")
        data.extend(header)

        for y in range(height):
            ratio = y / max(1, height - 1)
            r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
            g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
            b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
            row = bytes([r, g, b]) * width
            data.extend(row)

        return bytes(data)
    
    def _run_image_assets(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        run_dir = self._ensure_image_run_dir(ctx.run_id)
        assets: List[Dict[str, Any]] = []

        for index, scene in enumerate(scenes, start=1):
            scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
            file_name = f"{scene_id}.ppm"
            output_path = run_dir / file_name
            output_path.write_bytes(
                self._build_scene_ppm(ctx, scene, index)
            )

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
            "provider": "scene_svg_builder",
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

        alternating_speakers = ["mother", "child"]

        for index, scene in enumerate(scenes, start=1):
            text = str(scene.get("narration", "")).strip()
            if not text:
                continue

            segments = [part.strip() for part in text.split("。") if part.strip()]
            if not segments:
                segments = [text]

            for seg_index, segment in enumerate(segments, start=1):
                speaker = alternating_speakers[(seg_index - 1) % len(alternating_speakers)]
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

    def _run_audio_segments(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        dialogue_script = outputs.get("dialogue_script") or {}
        lines = dialogue_script.get("lines") or []

        if not dialogue_script.get("enabled") or not lines:
            empty_directory_manifest = self._write_audio_directory_manifest(ctx.run_id, [])
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
            char_count = max(1, len(text))
            duration_estimate_sec = max(2, min(12, char_count // 8))

            file_name = f"{speaker}_{index:02d}.mp3"
            relative_path = f"assets/mock/audio/{ctx.run_id}/{file_name}"
            public_url = f"/assets/mock/audio/{ctx.run_id}/{file_name}"
            output_path = run_dir / file_name
            waveform_preview = [
                max(0.12, round(duration_estimate_sec / 12, 2)),
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
                    asset_metadata = {
                        "tts_model": tts_result.get("model"),
                        "tts_voice": tts_result.get("voice"),
                        "output_bytes": tts_result.get("output_bytes"),
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
                "scene_id": scene_id,
                "speaker": speaker,
                "voice_style": voice_style,
                "provider": generation_provider,
                "file_name": file_name,
                "relative_path": relative_path,
                "public_url": public_url,
                "mime_type": "audio/mpeg",
                "duration_estimate_sec": duration_estimate_sec,
                "asset_status": asset_status,
                "generation_mode": generation_mode,
                "waveform_preview": waveform_preview,
                "metadata": asset_metadata,
            }

            item = {
                "segment_id": f"audio_{index:02d}",
                "scene_id": scene_id,
                "speaker": speaker,
                "text": text,
                "voice_style": voice_style,
                "target_audio_file": relative_path,
                "duration_estimate_sec": duration_estimate_sec,
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

        narration = outputs.get("narration") or {}
        segments = narration.get("segments") or []

        items: List[Dict[str, Any]] = []
        current_start = 0
        srt_lines: List[str] = []

        for index, segment in enumerate(segments, start=1):
            text = str(segment.get("text", ""))
            duration = max(3, ctx.input.duration_sec // max(1, len(segments)))
            start_sec = current_start
            end_sec = current_start + duration
            current_start = end_sec

            item = {
                "index": index,
                "scene_id": segment.get("scene_id"),
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": text,
            }
            items.append(item)

            srt_lines.extend(
                [
                    str(index),
                    f"00:00:{start_sec:02d},000 --> 00:00:{end_sec:02d},000",
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

        image_by_scene = {
            str(item.get("scene_id")): item
            for item in image_assets_list
            if item.get("scene_id")
        }

        concat_lines: List[str] = []
        video_run_dir = self._ensure_video_run_dir(ctx.run_id)
        concat_file = video_run_dir / "scene_concat.txt"

        for item in audio_items:
            scene_id = str(item.get("scene_id") or "")
            image_asset = image_by_scene.get(scene_id)
            if not image_asset:
                continue

            image_path = PROJECT_ROOT / str(image_asset.get("relative_path"))
            duration_sec = max(1, int(item.get("duration_estimate_sec") or 3))
            escaped_image_path = str(image_path).replace("'", "'\\''")

            concat_lines.append(f"file '{escaped_image_path}'")
            concat_lines.append(f"duration {duration_sec}")

        if image_assets_list:
            last_image_asset = image_assets_list[-1]
            last_image_path = PROJECT_ROOT / str(last_image_asset.get("relative_path"))
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

        video_run_dir = self._ensure_video_run_dir(ctx.run_id)
        concat_file = self._build_video_concat_file(ctx, image_assets, audio_segments)

        audio_manifest = audio_segments.get("asset_manifest") or {}
        audio_assets = audio_manifest.get("assets") or []
        audio_file_paths = [
            str(PROJECT_ROOT / str(asset.get("relative_path")))
            for asset in audio_assets
            if asset.get("relative_path")
        ]

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

        final_video_path = video_run_dir / "final.mp4"

        subtitle_filter = f"subtitles=filename=assets/mock/video/{ctx.run_id}/subtitles.srt"

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
                "-i",
                str(merged_audio_path),
                "-vf",
                subtitle_filter,
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
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
            "duration_sec": ctx.input.duration_sec,
            "audio_track_path": f"assets/mock/video/{ctx.run_id}/merged_audio.mp3",
            "subtitle_path": f"assets/mock/video/{ctx.run_id}/subtitles.srt",
        }