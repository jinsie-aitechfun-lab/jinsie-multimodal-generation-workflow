from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import uuid4

from app.schemas.workflow import StepResult, WorkflowRunRequest, WorkflowRunResponse


class UnknownStepError(Exception):
    pass


@dataclass(frozen=True)
class StepContext:
    workflow_id: str
    run_id: str
    input: Dict[str, Any]


class WorkflowRunner:
    """
    Day56 minimum runner:
    - sequential steps
    - structured outputs
    - placeholder implementations only
    """

    def __init__(self) -> None:
        self._handlers = {
            "story": self._run_story,
            "image": self._run_image,
            "audio": self._run_audio,
            "video": self._run_video,
        }

    def run(self, req: WorkflowRunRequest) -> WorkflowRunResponse:
        run_id = f"run_{uuid4().hex[:12]}"
        ctx = StepContext(workflow_id=req.workflow_id, run_id=run_id, input=req.input)

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
            run_id=run_id,
            status="COMPLETED",
            steps=step_results,
            outputs=aggregated_outputs,
            timestamp=WorkflowRunResponse.now_timestamp(),
        )

    def _run_story(self, ctx: StepContext, outputs: Dict[str, Any]) -> Dict[str, Any]:
        topic = str(ctx.input.get("topic", "一个小故事"))
        audience = str(ctx.input.get("audience", "general"))
        text = f"这是一个关于「{topic}」的故事（audience={audience}）。"
        return {"text": text}

    def _run_image(self, ctx: StepContext, outputs: Dict[str, Any]) -> Dict[str, Any]:
        story_text = (outputs.get("story") or {}).get("text", "")
        prompt = "一幅温暖、童趣、色彩柔和的插画风格画面"
        if story_text:
            prompt = f"{prompt}，围绕故事内容：{story_text}"
        return {"image_prompt": prompt}

    def _run_audio(self, ctx: StepContext, outputs: Dict[str, Any]) -> Dict[str, Any]:
        story_text = (outputs.get("story") or {}).get("text", "")
        return {"tts_text": story_text or "（占位）配音文本", "voice_style": "warm_female"}

    def _run_video(self, ctx: StepContext, outputs: Dict[str, Any]) -> Dict[str, Any]:
        image_prompt = (outputs.get("image") or {}).get("image_prompt", "")
        tts_text = (outputs.get("audio") or {}).get("tts_text", "")
        return {
            "video_plan": {
                "scenes": 4,
                "image_prompt": image_prompt,
                "narration": tts_text,
                "note": "Day56 placeholder，不生成真实视频，只返回结构化计划",
            }
        }