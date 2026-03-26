from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepSpec(BaseModel):
    name: str = Field(
        ...,
        description=(
            "Step name, e.g. "
            "story/storyboard/image_prompts/video_prompts/"
            "dialogue_script/narration/subtitles/render_plan"
        ),
    )


class WorkflowInput(BaseModel):
    topic: str = Field(..., description="Story topic or user prompt")
    audience: str = Field(default="children")
    tone: str = Field(default="warm")
    visual_style: str = Field(default="storybook")
    character_style: str = Field(default="animal")
    voice_style: str = Field(default="warm_female")
    voiceover_enabled: bool = Field(default=False)
    voice_mode: str = Field(default="single")
    speaker_profiles: Dict[str, str] = Field(
        default_factory=lambda: {
            "narrator": "warm_female",
            "mother": "warm_female",
            "child": "gentle_child",
        }
    )
    duration_sec: int = Field(default=60, ge=15, le=300)
    language: str = Field(default="zh-CN")
    subtitle_enabled: bool = Field(default=True)
    video_provider: str = Field(default="mock")
    output_mode: str = Field(default="full_video")


class WorkflowRunRequest(BaseModel):
    workflow_id: str
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session identifier for future multi-turn workflow memory",
    )
    input: WorkflowInput
    steps: List[StepSpec]


class StepResult(BaseModel):
    name: str
    status: str
    output: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRunResponse(BaseModel):
    workflow_id: str
    session_id: Optional[str] = None
    run_id: str
    status: str
    steps: List[StepResult]
    outputs: Dict[str, Any] = Field(default_factory=dict)
    session_memory_summary: Dict[str, Any] = Field(default_factory=dict)
    render_package: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str

    @staticmethod
    def now_timestamp() -> str:
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )