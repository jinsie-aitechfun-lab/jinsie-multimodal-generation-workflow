"""Contract verification for runner refactor Step 17.

Verifies RunnerSingleSceneImageSupport owns single-scene API image asset
generation while WorkflowRunner keeps a thin compatibility wrapper. The test
uses a fake API adapter and does not call any external image service.

Usage:
    python scripts/verify_step17_single_scene_api_image.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import StepContext, WorkflowRunner
import app.services.runner_single_scene_image_support as single_scene_module


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05"
    b"\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
)


SCENE = {
    "scene_id": "scene_01",
    "scene_title": "一起过河",
    "visual_description": "小兔子和小乌龟站在河边。",
    "narration": "两个朋友来到河边。",
    "shot_type": "wide",
    "characters": [
        {
            "character_id": "char_primary_01",
            "display_name": "小兔子",
            "role_type": "primary",
        },
        {
            "character_id": "char_secondary_01",
            "display_name": "小乌龟",
            "role_type": "secondary",
        },
    ],
}


class FakeApiImageGeneratorAdapter:
    tasks = []

    def __init__(self, runner):
        self._runner = runner

    def generate(self, task):
        self.tasks.append(task)
        return PNG_BYTES


def make_ctx(run_id: str) -> StepContext:
    return StepContext(
        workflow_id="verify_step17",
        session_id=None,
        run_id=run_id,
        input=WorkflowInput(
            topic="写一个关于小兔子和小乌龟过河的故事",
            duration_sec=60,
        ),
    )


def main() -> int:
    runner = WorkflowRunner()
    original_adapter = single_scene_module.ApiImageGeneratorAdapter
    FakeApiImageGeneratorAdapter.tasks = []

    assets_root = PROJECT_ROOT / "assets" / "mock" / "image"
    assets_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="verify_step17_", dir=assets_root) as tmp:
        run_id = Path(tmp).name
        ctx = make_ctx(run_id)
        outputs = {
            "storyboard": {
                "scenes": [SCENE],
            },
            "image_prompts": {
                "prompts": [
                    {
                        "scene_id": "scene_01",
                        "shot_id": "shot_01",
                        "scene_title": "一起过河 prompt",
                        "characters": SCENE["characters"],
                        "prompt": "storybook prompt with white rabbit and green turtle",
                    }
                ]
            },
        }

        single_scene_module.ApiImageGeneratorAdapter = FakeApiImageGeneratorAdapter
        try:
            asset = runner._run_single_scene_api_image_asset(
                ctx=ctx,
                outputs=outputs,
                scene=SCENE,
                scene_index=1,
            )
            direct_asset = runner._single_scene_image_support.run_single_scene_api_image_asset(
                ctx=ctx,
                outputs=outputs,
                scene=SCENE,
                scene_index=1,
            )
        finally:
            single_scene_module.ApiImageGeneratorAdapter = original_adapter

        assert asset == direct_asset

        assert asset["scene_id"] == "scene_01"
        assert asset["scene_title"] == "一起过河 prompt"
        assert asset["status"] == "generated"
        assert asset["prompt"] == "storybook prompt with white rabbit and green turtle"
        assert asset["selected_asset_ref"]["provider"] == "api_image_generator"
        assert asset["selection_source"] == "auto_filter"
        assert len(asset["candidate_asset_refs"]) == 2
        assert len(asset["candidate_scores"]) == 2

        task_prompts = [task.prompt for task in FakeApiImageGeneratorAdapter.tasks]
        assert len(task_prompts) == 4
        assert task_prompts[0] == "storybook prompt with white rabbit and green turtle"
        assert "alternate composition" in task_prompts[1]
        assert task_prompts[2] == "storybook prompt with white rabbit and green turtle"
        assert "alternate composition" in task_prompts[3]

        for suffix in ["candidate_a", "candidate_b"]:
            output_path = Path(tmp) / f"scene_01__{suffix}.png"
            assert output_path.exists()
            assert output_path.read_bytes() == PNG_BYTES

    print("[OK] single-scene API candidate generation contract")
    print("[OK] single-scene API selection metadata contract")
    print("[OK] runner single-scene API proxy contract")
    print("PASS: Step 17 single scene API image support contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
