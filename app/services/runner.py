from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

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
    """

    def __init__(self) -> None:
        self._handlers = {
            "story": self._run_story,
            "storyboard": self._run_storyboard,
            "image_prompts": self._run_image_prompts,
            "video_prompts": self._run_video_prompts,
            "narration": self._run_narration,
            "subtitles": self._run_subtitles,
            "render_plan": self._run_render_plan,
        }

    def run(self, req: WorkflowRunRequest) -> WorkflowRunResponse:
        run_id = f"run_{uuid4().hex[:12]}"
        ctx = StepContext(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=run_id,
            input=req.input,
        )

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

        return WorkflowRunResponse(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=run_id,
            status="COMPLETED",
            steps=step_results,
            outputs=aggregated_outputs,
            timestamp=WorkflowRunResponse.now_timestamp(),
        )

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

    def _scene_blueprints(self, ctx: StepContext, scene_count: int) -> List[Dict[str, str]]:
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
        for index, (segment, blueprint) in enumerate(zip(story_parts, blueprints), start=1):
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

    def _run_video_prompts(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        return self._build_video_provider_prompts(ctx, scenes)

    def _run_narration(
        self, ctx: StepContext, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                    "text": text,
                    "voice_style": ctx.input.voice_style,
                }
            )

        return {
            "voice_style": ctx.input.voice_style,
            "language": ctx.input.language,
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