import json
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi import Body
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
from app.services.cancellation import (
    clear as _clear_cancel,
    is_cancelled as _is_cancelled,
    request_cancel as _request_cancel,
)
from app.services.runner import UnknownStepError, WorkflowRunner
from app.services.runner_errors import WorkflowCancelledError

app = FastAPI(title="jinsie-multimodal-generation-workflow", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
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


@app.on_event("startup")
def _abandon_orphaned_workflows() -> None:
    """Clean up status files that survived a previous server crash / restart.

    When uvicorn dies in the middle of a workflow run, the per-workflow
    status.json is left at "processing" or "cancel_requested" forever.
    A subsequent client reattach reads that stale status, enters the
    cancelling-UI state, and polls forever because no process is going
    to advance the status to a terminal value. Mark these as
    "abandoned" on startup so the frontend can treat them as a clean
    terminal state and recover.
    """
    mock_dir = ASSETS_DIR / "mock"
    if not mock_dir.exists():
        return

    transient_states = {"processing", "cancel_requested"}
    rewritten = 0
    for status_path in mock_dir.glob("*/status.json"):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                continue
            data = json.loads(content)
            existing = str(data.get("status") or "").strip().lower()
            if existing not in transient_states:
                continue
            data["status"] = "abandoned"
            data["abandoned_at"] = int(time.time())
            data["abandoned_reason"] = (
                f"server restarted while workflow status was '{existing}'"
            )
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            rewritten += 1
        except (OSError, json.JSONDecodeError):
            # Corrupt or unreadable status file — leave it; the frontend
            # 404 path / polling timeout will eventually handle it.
            continue

    if rewritten:
        print(
            f"[startup] marked {rewritten} orphaned workflow(s) as 'abandoned'"
        )


@app.get("/health")
def health():
    return {"status": "ok"}


def _refresh_scene_error_detail(req: ImageReviewRefreshSceneRequest, error: Exception):
    try:
        provider = _runner._image_provider_name()
    except Exception:
        provider = "unknown"

    return {
        "code": "IMAGE_GENERATION_FAILED",
        "scene_id": req.scene_id,
        "provider": provider,
        "message": str(error) or error.__class__.__name__,
    }


def _workflow_dir(workflow_id: str) -> Path:
    return ASSETS_DIR / "mock" / str(workflow_id)


def _workflow_status_path(workflow_id: str) -> Path:
    return _workflow_dir(workflow_id) / "status.json"


def _workflow_outputs_path(workflow_id: str) -> Path:
    return _workflow_dir(workflow_id) / "outputs.json"


def _patch_workflow_outputs(workflow_id: str, patch: dict) -> None:
    """Merge patch fields into the stored outputs.json for a workflow run."""
    path = _workflow_outputs_path(workflow_id)
    if not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        outputs = data.get("outputs") or {}
        outputs.update(patch)
        data["outputs"] = outputs
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[patch_workflow_outputs] failed to patch {workflow_id}: {e}")


def _write_workflow_status(
    workflow_id: str,
    status: str,
    *,
    detail: dict | None = None,
) -> dict:
    payload = {
        "workflow_id": workflow_id,
        "status": status,
        "updated_at": int(time.time()),
    }
    if detail:
        payload.update(detail)

    out_dir = _workflow_dir(workflow_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(_workflow_status_path(workflow_id), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


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


@app.post("/v1/workflow/run")
def run_workflow(req: dict = Body(...)):
    workflow_id = req.get("workflow_id") or f"wf_{int(time.time()*1000)}"
    requested_steps = req.get("steps") or []
    first_step = requested_steps[0] if requested_steps else {}
    first_step_name = (
        first_step.get("name") if isinstance(first_step, dict) else None
    )
    _write_workflow_status(
        workflow_id,
        "processing",
        detail={
            "current_step": first_step_name or "",
            "current_step_index": 1 if first_step_name else 0,
            "completed_steps": 0,
            "total_steps": len(requested_steps),
            "progress_percent": 0,
        },
    )

    def on_complete(outputs: dict):
        out_dir = _workflow_dir(workflow_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(_workflow_outputs_path(workflow_id), "w", encoding="utf-8") as f:
            json.dump(outputs, f, ensure_ascii=False, indent=2)
        _write_workflow_status(workflow_id, "completed")
        _clear_cancel(workflow_id)
        print(f"[AsyncRunner] workflow {workflow_id} completed.")

    def on_error(error: Exception):
        # Distinguish user-initiated cancel from real failures so the
        # client can tell them apart in the status UI.
        if isinstance(error, WorkflowCancelledError):
            _write_workflow_status(
                workflow_id,
                "cancelled",
                detail={"message": "user cancelled"},
            )
            _clear_cancel(workflow_id)
            print(f"[AsyncRunner] workflow {workflow_id} cancelled by user.")
            return
        _write_workflow_status(
            workflow_id,
            "failed",
            detail={"message": str(error) or error.__class__.__name__},
        )
        _clear_cancel(workflow_id)

    def on_progress(progress: dict):
        # A cancel request might land before the runner reaches its next
        # checkpoint — keep the file status as "cancel_requested" rather
        # than letting later progress events overwrite it.
        if _is_cancelled(workflow_id):
            return
        _write_workflow_status(workflow_id, "processing", detail=progress)

    _runner._run_async(
        req.dict() if hasattr(req, "dict") else dict(req),
        callback=on_complete,
        error_callback=on_error,
        progress_callback=on_progress,
    )

    return {"workflow_id": workflow_id, "status": "processing"}


@app.post("/v1/workflow/cancel")
def cancel_workflow(req: dict = Body(...)):
    """Mark an in-flight workflow for cancellation.

    The runner polls the cancellation registry at each step boundary and
    raises WorkflowCancelledError when the flag is set. This endpoint
    only flips the flag and reflects the request in the status file;
    actual cancellation takes effect at the next checkpoint, so the UI
    should show "cancel_requested" until the runner reaches one.
    """
    workflow_id = str(req.get("workflow_id") or "").strip()
    if not workflow_id:
        raise HTTPException(status_code=400, detail="workflow_id is required")

    # If the workflow already settled, there's nothing to cancel.
    status_path = _workflow_status_path(workflow_id)
    if status_path.exists():
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                existing = json.loads(content)
                existing_status = str(existing.get("status") or "").strip().lower()
                if existing_status in {"completed", "failed", "cancelled"}:
                    return {
                        "workflow_id": workflow_id,
                        "status": existing_status,
                        "already_settled": True,
                    }
        except (json.JSONDecodeError, OSError):
            pass

    _request_cancel(workflow_id)
    _write_workflow_status(
        workflow_id,
        "cancel_requested",
        detail={"message": "user requested cancel"},
    )
    return {"workflow_id": workflow_id, "status": "cancel_requested"}


@app.get("/v1/workflow/status/{workflow_id}")
def get_workflow_status(workflow_id: str):
    status_path = _workflow_status_path(workflow_id)
    if status_path.exists():
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            pass
        return {"workflow_id": workflow_id, "status": "processing"}

    if _workflow_outputs_path(workflow_id).exists():
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "updated_at": int(_workflow_outputs_path(workflow_id).stat().st_mtime),
        }

    raise HTTPException(status_code=404, detail=f"workflow not found: {workflow_id}")


@app.get("/v1/workflow/results/{workflow_id}")
def get_workflow_results(workflow_id: str):
    outputs_path = _workflow_outputs_path(workflow_id)
    if not outputs_path.exists():
        raise HTTPException(status_code=404, detail=f"workflow results not found: {workflow_id}")
    try:
        with open(outputs_path, "r", encoding="utf-8") as f:
            outputs = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"failed to read workflow results: {e}")
    return outputs


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
        # Persist final_video back to outputs.json so that page refresh can
        # detect the already-generated video and skip re-rendering.
        _patch_workflow_outputs(req.workflow_id, {
            "final_video": result["final_video"],
        })
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
            character_manifest=getattr(req, "character_manifest", None),
            image_prompts=getattr(req, "image_prompts", None),
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


@app.post(
    "/v1/image-review/refresh-scene", response_model=ImageReviewRefreshSceneResponse
)
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
            character_manifest=req.character_manifest,
            image_prompts=req.image_prompts,
            video_provider=req.video_provider,
            preserve_seed=req.preserve_seed,
            known_failed_scene_ids=list(req.known_failed_scene_ids or []),
        )
        print("[image-review] refresh-scene completed", req.run_id, req.scene_id)

        # Persist updated image_review + image_assets back to outputs.json so that
        # page refresh loads the real generated state instead of the frozen pending state.
        _patch_workflow_outputs(req.workflow_id, {
            "image_review": result["image_review"],
            "image_assets": result["image_assets"],
        })

        return ImageReviewRefreshSceneResponse(
            workflow_id=result["workflow_id"],
            session_id=result.get("session_id"),
            run_id=result["run_id"],
            scene_id=result["scene_id"],
            scene_image_asset=result["scene_image_asset"],
            scene_review_item=result["scene_review_item"],
            image_assets=result["image_assets"],
            image_review=result["image_review"],
            video_prompts=result["video_prompts"],
            timestamp=ImageReviewRefreshSceneResponse.now_timestamp(),
        )
    except ValueError as e:
        print("[image-review] refresh-scene bad request", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("[image-review] refresh-scene runtime error", repr(e))
        # On terminal failure we need to write outputs.json such that the
        # FE can see this scene as failed even if it had a *prior*
        # successful selection (i.e. user retried an already-generated
        # scene and the retry blew up). Steps:
        #   1. drop the current scene from image_review.selected_assets
        #      so the helper doesn't emit a stale `generated` entry for
        #      it (which would mask the failure)
        #   2. add the current scene to known_failed_scene_ids so the
        #      helper emits a `failed` placeholder
        #   3. patch BOTH image_assets and (if modified) image_review to
        #      disk so a page reload sees the same state
        #   4. embed the rebuilt assets+review in the 502 detail so the
        #      FE can update its in-memory state without a reload
        rebuilt_image_assets = None
        rebuilt_image_review: dict | None = None
        try:
            failed_ids = list(req.known_failed_scene_ids or [])
            current_scene = str(req.scene_id or "").strip()
            if current_scene and current_scene not in failed_ids:
                failed_ids.append(current_scene)

            review_for_fallback: dict = dict(req.image_review or {})
            prior_selected = review_for_fallback.get("selected_assets") or []
            review_changed = False
            if isinstance(prior_selected, list) and current_scene:
                kept = [
                    s for s in prior_selected
                    if not (
                        isinstance(s, dict)
                        and str(s.get("scene_id") or "").strip() == current_scene
                    )
                ]
                if len(kept) != len(prior_selected):
                    review_for_fallback["selected_assets"] = kept
                    review_for_fallback["selected_count"] = len(kept)
                    review_changed = True

            storyboard_scenes = (req.storyboard or {}).get("scenes") or []
            rebuilt_image_assets = _runner.build_image_assets_from_selected_assets(
                run_id=req.run_id,
                image_review=review_for_fallback,
                provider=str(_runner._image_provider_name()),
                storyboard_scenes=storyboard_scenes,
                known_failed_scene_ids=failed_ids,
            )

            patch: dict = {"image_assets": rebuilt_image_assets}
            if review_changed:
                rebuilt_image_review = review_for_fallback
                patch["image_review"] = review_for_fallback
            _patch_workflow_outputs(req.workflow_id, patch)
        except Exception as persist_err:
            print("[image-review] failed to persist failure", repr(persist_err))

        detail = _refresh_scene_error_detail(req, e)
        if rebuilt_image_assets is not None:
            detail["image_assets"] = rebuilt_image_assets
        if rebuilt_image_review is not None:
            detail["image_review"] = rebuilt_image_review
        raise HTTPException(
            status_code=502,
            detail=detail,
        ) from e


from fastapi import Body
