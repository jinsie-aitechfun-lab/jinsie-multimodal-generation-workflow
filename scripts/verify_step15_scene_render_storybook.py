"""Contract verification for runner refactor Step 15.

Verifies RunnerSceneRenderStorybookSupport keeps the normal Pillow storybook
renderer and runner proxy behavior stable after extracting _build_scene_ppm
and _build_scene_png from WorkflowRunner.

Usage:
    python scripts/verify_step15_scene_render_storybook.py
"""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import StepContext, WorkflowRunner


SCENE = {
    "scene_id": "scene_02",
    "scene_title": "岔路口",
    "visual_description": "小兔子站在温柔的岔路口，认真思考方向。",
    "narration": "小兔子停下来，想一想再出发。",
    "duration_sec": 12,
    "shot_type": "medium",
    "transition": "fade",
}


def make_ctx() -> StepContext:
    return StepContext(
        workflow_id="verify_step15",
        session_id=None,
        run_id="run_verify_step15",
        input=WorkflowInput(
            topic="写一个关于小兔子走过岔路口的故事",
            duration_sec=60,
        ),
    )


def assert_ppm_frame(data: bytes) -> None:
    assert data.startswith(b"P6\n1280 720\n255\n")
    header_length = len(b"P6\n1280 720\n255\n")
    assert len(data) == header_length + 1280 * 720 * 3
    assert len(set(data[header_length : header_length + 3000])) > 1


def main() -> int:
    runner = WorkflowRunner()
    support = runner._scene_render_storybook
    ctx = make_ctx()

    runner_ppm = runner._build_scene_ppm(ctx, SCENE, 2)
    support_ppm = support.build_scene_ppm(ctx, SCENE, 2)
    assert runner_ppm == support_ppm
    assert_ppm_frame(runner_ppm)

    runner_png = runner._build_scene_png(ctx, SCENE, 2)
    support_png = support.build_scene_png(ctx, SCENE, 2)
    assert runner_png == support_png
    assert runner_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(runner_png) > 1000

    original_import = builtins.__import__

    def blocked_pil_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("forced PIL import failure")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = blocked_pil_import
    try:
        fallback_ppm = runner._build_scene_ppm(ctx, SCENE, 2)
    finally:
        builtins.__import__ = original_import

    assert_ppm_frame(fallback_ppm)

    print("[OK] storybook scene PPM proxy contract")
    print("[OK] storybook scene PNG proxy contract")
    print("[OK] storybook renderer fallback delegation contract")
    print("PASS: Step 15 scene render storybook support contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
