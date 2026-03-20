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

    def _split_story_segments(self, text: str, scene_count: int) -> List[str]:
        cleaned = text.replace("。", "。|").replace("！", "！|").replace("？", "？|")
        parts = [item.strip() for item in cleaned.split("|") if item.strip()]
        if not parts:
            parts = [text]

        if len(parts) >= scene_count:
            return parts[:scene_count]

        while len(parts) < scene_count:
            parts.append(parts[-1])

        return parts

    def _run_story(self, ctx: StepContext, outputs: Dict[str, Any]) -> Dict[str, Any]:
        topic = ctx.input.topic.strip() or "一个温暖的童话故事"
        title = f"{topic}的故事"
        summary = (
            f"面向{ctx.input.audience}，采用{ctx.input.tone}语气，"
            f"以{ctx.input.character_style}角色风格展开。"
        )
        text = (
            f"在一个{ctx.input.tone}的世界里，主角围绕“{topic}”展开了一段冒险。"
            f"故事整体面向{ctx.input.audience}，画面适合{ctx.input.visual_style}风格呈现。"
            f"旅途中主角经历了发现问题、尝试行动、获得帮助、最终成长四个阶段，"
            f"最后收获了勇气、陪伴与温暖。"
        )
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
        scene_count = self._scene_count(ctx.input.duration_sec)
        segments = self._split_story_segments(story_text, scene_count)
        duration_per_scene = max(5, ctx.input.duration_sec // scene_count)

        scenes: List[Dict[str, Any]] = []
        for index, segment in enumerate(segments, start=1):
            scenes.append(
                {
                    "scene_id": f"scene_{index:02d}",
                    "scene_title": f"第{index}幕",
                    "visual_description": (
                        f"{ctx.input.visual_style}风格画面，突出{ctx.input.character_style}主角，"
                        f"氛围为{ctx.input.tone}。"
                    ),
                    "narration": segment,
                    "duration_sec": duration_per_scene,
                    "shot_type": "medium",
                    "transition": "fade",
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

        prompts: List[Dict[str, Any]] = []
        for scene in scenes:
            narration = str(scene.get("narration", ""))
            visual_description = str(scene.get("visual_description", ""))
            prompt = (
                f"Create a short animated video shot in {ctx.input.visual_style} style, "
                f"{ctx.input.tone} atmosphere, with {ctx.input.character_style} characters. "
                f"Scene description: {visual_description}. Narration context: {narration}"
            )
            prompts.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "prompt": prompt,
                    "provider": ctx.input.video_provider,
                }
            )

        return {"provider": ctx.input.video_provider, "prompts": prompts}

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

        asset_plan: List[Dict[str, Any]] = []
        for scene in scenes:
            asset_plan.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "image_required": True,
                    "video_required": True,
                    "audio_required": True,
                    "subtitle_required": bool(subtitles.get("enabled")),
                }
            )

        return {
            "provider": ctx.input.video_provider,
            "output_mode": ctx.input.output_mode,
            "total_duration_sec": ctx.input.duration_sec,
            "scene_count": len(scenes),
            "asset_plan": asset_plan,
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