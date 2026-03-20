from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepSpec(BaseModel):
    name: str = Field(..., description="Step name, e.g. story/image/audio/video")


class WorkflowRunRequest(BaseModel):
    workflow_id: str
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session identifier for future multi-turn workflow memory",
    )
    input: Dict[str, Any] = Field(default_factory=dict)
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
    timestamp: str

    @staticmethod
    def now_timestamp() -> str:
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )