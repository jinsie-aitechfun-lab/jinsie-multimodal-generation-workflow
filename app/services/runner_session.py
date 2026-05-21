from __future__ import annotations

from typing import Any, Dict, Optional

from app.schemas.workflow import WorkflowRunRequest


class RunnerSessionStore:
    """In-memory store for per-session history and per-run context.

    Extracted from WorkflowRunner as part of the runner refactor.
    Behavior must remain byte-for-byte identical to the original methods
    in runner.py; this class owns the two dicts that previously lived
    directly on WorkflowRunner (`_session_store`, `_run_store`).
    """

    def __init__(self) -> None:
        self._session_store: Dict[str, Dict[str, Any]] = {}
        self._run_store: Dict[str, Dict[str, Any]] = {}

    def get_session_data(
        self, session_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        return self._session_store.get(session_id)

    def save_session_data(
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

    def get_run_context(self, run_id: str) -> Optional[Dict[str, Any]]:
        normalized_run_id = str(run_id or "").strip()
        if not normalized_run_id:
            return None
        return self._run_store.get(normalized_run_id)

    def save_run_context(
        self,
        *,
        workflow_id: str,
        session_id: Optional[str],
        run_id: str,
        outputs: Dict[str, Any],
        workflow_input: Dict[str, Any],
    ) -> None:
        normalized_run_id = str(run_id or "").strip()
        if not normalized_run_id:
            return

        self._run_store[normalized_run_id] = {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "workflow_input": dict(workflow_input or {}),
            "character_manifest": outputs.get("character_manifest") or {},
            "storyboard": outputs.get("storyboard") or {},
            "sentence_shots": outputs.get("sentence_shots") or {},
            "image_prompts": outputs.get("image_prompts") or {},
            "image_assets": outputs.get("image_assets") or {},
            "image_review": outputs.get("image_review") or {},
            "video_prompts": outputs.get("video_prompts") or {},
        }

    def build_session_memory_summary(
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
