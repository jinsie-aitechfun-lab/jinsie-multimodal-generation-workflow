from __future__ import annotations
from typing import Any, Dict
from app.schemas.workflow import WorkflowInput, WorkflowRunRequest
from app.services.runner_audio_render_support import RunnerAudioRenderSupport
from app.services.runner_image_selection_support import RunnerImageSelectionSupport
from app.services.runner_single_scene_image_support import RunnerSingleSceneImageSupport
from app.services.image_candidate_selector import select_best_candidate
from app.services.character_visual_profile_llm import build_llm_character_visual_profiles

class WorkflowRunnerCore:
    def __init__(self):
        self._audio_render_support = RunnerAudioRenderSupport(self)
        self._image_selection_support = RunnerImageSelectionSupport(self)
        self._single_scene_image_support = RunnerSingleSceneImageSupport(self)

    def run(self, request: WorkflowRunRequest) -> Dict[str, Any]:
        outputs: Dict[str, Any] = {}

        # story placeholder
        outputs["story"] = {"text": "测试故事内容"}

        # storyboard placeholder
        outputs["storyboard"] = {"scenes": [{"scene_id": "scene_001"}]}

        # image candidate selection (no arguments)
        images = select_best_candidate()
        outputs["image_assets"] = images

        # multi-character profile enhancement
        characters = build_llm_character_visual_profiles(manifest=[], scene={})
        outputs["character_profiles"] = characters

        # audio / video render
        self._audio_render_support.run_final_video(request, outputs)

        return outputs