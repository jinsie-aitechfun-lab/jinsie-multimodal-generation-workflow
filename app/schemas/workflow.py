from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StepSpec(BaseModel):
    name: str = Field(
        ...,
        description=(
            "Step name, e.g. "
            "story/storyboard/image_prompts/image_assets/video_prompts/"
            "dialogue_script/audio_segments/narration/subtitles/render_plan/final_video"
        ),
    )


class StructuredCharacterInput(BaseModel):
    display_name: str = Field(
        ...,
        min_length=1,
        description="Character display name, e.g. 小兔子 / 小乌龟",
    )
    species: str = Field(
        ...,
        min_length=1,
        description="Character species, e.g. rabbit / turtle / fox / cat",
    )
    role_type: Literal["primary", "secondary"] = Field(
        default="primary",
        description="Character role type",
    )
    visual_traits: str = Field(
        default="",
        description="Free-form visual traits, e.g. long upright ears, red scarf",
    )
    forbidden_traits: str = Field(
        default="",
        description="Free-form forbidden traits, e.g. no shell, no cat ears",
    )


class WorkflowInput(BaseModel):
    topic: str = Field(..., description="Story topic or user prompt")
    audience: str = Field(default="children")
    tone: str = Field(default="warm")
    visual_style: str = Field(default="storybook")
    character_style: str = Field(default="animal")

    main_character: str = Field(
        default="",
        description="Concrete main character entity, free-form text",
    )
    main_character_display: str = Field(
        default="",
        description="Display name for story/subtitle rendering, e.g. 小兔子",
    )
    main_character_species: str = Field(
        default="rabbit",
        description="Main character species, e.g. rabbit / fox / cat / bear / deer",
    )
    main_character_visual_traits: str = Field(
        default="",
        description=(
            "Optional visual traits for main character, "
            "e.g. long upright ears, white tail, no shell"
        ),
    )
    image_generation_mode: str = Field(
        default="single_pass",
        description="Image generation mode: single_pass or split_compose",
    )
    main_character_position: str = Field(
        default="right",
        description="Main character position in composed image: left / center / right",
    )
    secondary_character_position: str = Field(
        default="left",
        description="Secondary character position in composed image: left / center / right",
    )
    secondary_character: str = Field(
        default="",
        description="Optional secondary character entity, free-form text",
    )
    secondary_character_display: str = Field(
        default="",
        description="Optional display name for secondary character, e.g. 小乌龟",
    )
    secondary_character_species: str = Field(
        default="turtle",
        description="Secondary character species, e.g. turtle / fox / cat / bear / dog",
    )
    secondary_character_visual_traits: str = Field(
        default="",
        description=(
            "Optional visual traits for secondary character, "
            "e.g. round shell, short legs, no rabbit ears"
        ),
    )
    character_consistency_anchor: str = Field(
        default="",
        description=(
            "Optional appearance anchor for consistent character rendering, "
            "e.g. white rabbit, long ears, red scarf"
        ),
    )

    structured_characters_enabled: bool = Field(
        default=False,
        description="Whether to enable structured character inputs for character finalization layer",
    )
    characters: List[StructuredCharacterInput] = Field(
        default_factory=list,
        description="Structured character list for character finalization layer",
    )

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
    character_speaker_profiles: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Optional voice profiles for character speaker mode, "
            "e.g. {'main_character': 'gentle_child', "
            "'secondary_character': 'warm_male', 'narrator': 'warm_female'}"
        ),
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
class ImageReviewSelectRequest(BaseModel):
    workflow_id: str
    session_id: Optional[str] = None
    run_id: str
    scene_id: str
    selected_asset_ref: Dict[str, Any] = Field(default_factory=dict)
    image_review: Dict[str, Any] = Field(default_factory=dict)
    video_provider: str = Field(default="mock")


class ImageReviewSelectResponse(BaseModel):
    workflow_id: str
    session_id: Optional[str] = None
    run_id: str
    scene_id: str
    image_review: Dict[str, Any] = Field(default_factory=dict)
    video_prompts: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str

    @staticmethod
    def now_timestamp() -> str:
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )