"""Contract verification for runner refactor Step 14.

Verifies mock scene rendering still returns a PNG on the primary Pillow path,
and the extracted pure-Python fallback returns a valid PPM when Pillow import
fails inside WorkflowRunner._build_scene_ppm.

Usage:
    python scripts/verify_step14_scene_render_fallback.py
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
    "scene_id": "scene_01",
    "scene_title": "星星小路",
    "visual_description": "小兔子沿着发光的小路向前走。",
    "narration": "夜晚，小兔子看见一条温柔发光的小路。",
    "duration_sec": 10,
    "shot_type": "wide",
    "transition": "fade",
}


def make_ctx() -> StepContext:
    return StepContext(
        workflow_id="verify_step14",
        session_id=None,
        run_id="run_verify_step14",
        input=WorkflowInput(
            topic="写一个关于小兔子寻找星星小路的故事",
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
    ctx = make_ctx()

    png_bytes = runner._build_scene_png(ctx, SCENE, 1)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png_bytes) > 1000

    original_import = builtins.__import__

    def blocked_pil_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("forced PIL import failure")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = blocked_pil_import
    try:
        fallback_ppm = runner._build_scene_ppm(ctx, SCENE, 1)
    finally:
        builtins.__import__ = original_import

    assert_ppm_frame(fallback_ppm)

    support_ppm = runner._scene_render_fallback.build_fallback_scene_ppm(
        ctx=ctx,
        scene=SCENE,
        index=1,
        theme={
            "sky_top": (109, 101, 255),
            "sky_bottom": (243, 236, 255),
            "accent": (120, 104, 255),
            "text_primary": (45, 39, 84),
            "text_secondary": (97, 91, 130),
            "shape_a": (255, 210, 218),
            "shape_b": (196, 229, 255),
            "shape_c": (216, 242, 220),
        },
        width=1280,
        height=720,
        topic=ctx.input.topic,
        scene_title=str(SCENE["scene_title"]),
        body_text=str(SCENE["narration"]),
        duration_sec=int(SCENE["duration_sec"]),
    )
    assert_ppm_frame(support_ppm)

    print("[OK] primary scene PNG render contract")
    print("[OK] extracted scene PPM fallback contract")
    print("PASS: Step 14 scene render fallback contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
