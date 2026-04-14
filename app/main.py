from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.schemas.workflow import (
    FinalVideoRenderRequest,
    FinalVideoRenderResponse,
    ImageReviewRefreshRequest,
    ImageReviewRefreshResponse,
    ImageReviewRefreshSceneRequest,
    ImageReviewRefreshSceneResponse,
    ImageReviewSelectRequest,
    ImageReviewSelectResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from app.services.runner import UnknownStepError, WorkflowRunner

app = FastAPI(title="jinsie-multimodal-generation-workflow", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_runner = WorkflowRunner()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/samples/summary")
def get_samples_summary():
    return _runner.get_samples_summary()


@app.get("/v1/samples/kling/real")
def get_real_kling_samples():
    return _runner.get_real_kling_samples_manifest()


@app.get("/v1/samples/kling/real/{sample_id}")
def get_real_kling_sample(sample_id: str):
    sample = _runner.get_real_kling_sample_by_id(sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"sample not found: {sample_id}")
    return sample


@app.post("/v1/workflow/run", response_model=WorkflowRunResponse)
def run_workflow(req: WorkflowRunRequest):
    print("[workflow] request received", req.workflow_id, req.session_id)
    try:
        result = _runner.run(req)
        print("[workflow] completed", result.run_id)
        return result
    except UnknownStepError as e:
        print("[workflow] unknown step error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("[workflow] runtime error", repr(e))
        raise


@app.post("/v1/image-review/select", response_model=ImageReviewSelectResponse)
def select_image_review_asset(req: ImageReviewSelectRequest):
    print("[image-review] selection request received", req.workflow_id, req.scene_id)
    try:
        result = _runner.update_image_review_selection(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=req.run_id,
            scene_id=req.scene_id,
            selected_asset_ref=req.selected_asset_ref,
            image_review=req.image_review,
            storyboard=req.storyboard,
            workflow_input=req.workflow_input,
            video_provider=req.video_provider,
        )
        print("[image-review] selection updated", req.run_id, req.scene_id)
        return ImageReviewSelectResponse(
            workflow_id=result["workflow_id"],
            session_id=result.get("session_id"),
            run_id=result["run_id"],
            scene_id=result["scene_id"],
            image_review=result["image_review"],
            image_assets=result.get("image_assets", {}),
            video_prompts=result["video_prompts"],
            timestamp=ImageReviewSelectResponse.now_timestamp(),
        )
    except ValueError as e:
        print("[image-review] bad request", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("[image-review] runtime error", repr(e))
        raise
@app.post("/v1/final-video/render", response_model=FinalVideoRenderResponse)
def render_final_video(req: FinalVideoRenderRequest):
    print("[final-video] render request received", req.workflow_id, req.run_id)
    try:
        result = _runner.rerender_final_video(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=req.run_id,
            workflow_input=req.workflow_input,
            image_assets=req.image_assets,
            audio_segments=req.audio_segments,
            subtitles=req.subtitles,
        )
        print("[final-video] render completed", req.run_id)
        return FinalVideoRenderResponse(
            workflow_id=result["workflow_id"],
            session_id=result.get("session_id"),
            run_id=result["run_id"],
            final_video=result["final_video"],
            timestamp=FinalVideoRenderResponse.now_timestamp(),
        )
    except ValueError as e:
        print("[final-video] bad request", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("[final-video] runtime error", repr(e))
        raise


@app.post("/v1/image-review/refresh", response_model=ImageReviewRefreshResponse)
def refresh_image_review(req: ImageReviewRefreshRequest):
    print("[image-review] refresh request received", req.workflow_id, req.run_id)
    try:
        result = _runner.refresh_image_review(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=req.run_id,
            storyboard=req.storyboard,
            workflow_input=req.workflow_input,
            image_review=req.image_review,
            video_provider=req.video_provider,
        )
        print("[image-review] refresh completed", req.run_id)
        return ImageReviewRefreshResponse(
            workflow_id=result["workflow_id"],
            session_id=result.get("session_id"),
            run_id=result["run_id"],
            image_assets=result["image_assets"],
            image_review=result["image_review"],
            video_prompts=result["video_prompts"],
            timestamp=ImageReviewRefreshResponse.now_timestamp(),
        )
    except ValueError as e:
        print("[image-review] refresh bad request", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("[image-review] refresh runtime error", repr(e))
        raise


@app.post("/v1/image-review/refresh-scene", response_model=ImageReviewRefreshSceneResponse)
def refresh_image_review_scene(req: ImageReviewRefreshSceneRequest):
    print(
        "[image-review] refresh-scene request received",
        req.workflow_id,
        req.run_id,
        req.scene_id,
    )
    try:
        result = _runner.refresh_image_review_scene(
            workflow_id=req.workflow_id,
            session_id=req.session_id,
            run_id=req.run_id,
            scene_id=req.scene_id,
            storyboard=req.storyboard,
            workflow_input=req.workflow_input,
            image_review=req.image_review,
            video_provider=req.video_provider,
        )
        print("[image-review] refresh-scene completed", req.run_id, req.scene_id)
        return ImageReviewRefreshSceneResponse(
            workflow_id=result["workflow_id"],
            session_id=result.get("session_id"),
            run_id=result["run_id"],
            scene_id=result["scene_id"],
            scene_image_asset=result["scene_image_asset"],
            scene_review_item=result["scene_review_item"],
            image_review=result["image_review"],
            video_prompts=result["video_prompts"],
            timestamp=ImageReviewRefreshSceneResponse.now_timestamp(),
        )
    except ValueError as e:
        print("[image-review] refresh-scene bad request", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("[image-review] refresh-scene runtime error", repr(e))
        raise