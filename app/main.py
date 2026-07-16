import json
import logging
import os
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


from app.schemas.workflow import (
    FinalVideoRenderRequest,
    FinalVideoRenderResponse,
    ImageReviewRefreshRequest,
    ImageReviewRefreshResponse,
    ImageReviewRefreshSceneRequest,
    ImageReviewRefreshSceneResponse,
    ImageReviewRefreshSceneTaskRequest,
    ImageReviewRefreshSceneTaskResponse,
    ImageReviewRefreshTaskBatchResponse,
    ImageReviewSelectRequest,
    ImageReviewSelectResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from app.services.atomic_json_store import read_json, update_json_atomic, write_json_atomic
from app.services.cache_control_static import RevalidatingStaticFiles
from app.services.cancellation import (
    clear as _clear_cancel,
    is_cancelled as _is_cancelled,
    request_cancel as _request_cancel,
)
from app.services.runner import UnknownStepError, WorkflowRunner
from app.services.runner_errors import WorkflowCancelledError
from app.services.image_refresh_tasks import (
    ImageRefreshCoordinator,
    ImageRefreshTaskManager,
)
from app.services.storage_ids import safe_child_dir, sanitize_storage_id

app = FastAPI(title="jinsie-multimodal-generation-workflow", version="0.1.0")
logger = logging.getLogger(__name__)

DEFAULT_CORS_ALLOW_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def _cors_allow_origins() -> list[str]:
    origins: list[str] = []
    for origin in DEFAULT_CORS_ALLOW_ORIGINS:
        if origin and origin not in origins:
            origins.append(origin)

    raw = os.getenv("CORS_ALLOW_ORIGINS", "")
    for origin in raw.split(","):
        value = origin.strip()
        if value and value not in origins:
            origins.append(value)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_runner = WorkflowRunner()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        RevalidatingStaticFiles(directory=str(ASSETS_DIR)),
        name="assets",
    )

_image_refresh_coordinator = ImageRefreshCoordinator(ASSETS_DIR, _runner)
_image_refresh_tasks = ImageRefreshTaskManager(ASSETS_DIR, _image_refresh_coordinator)


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
    _image_refresh_tasks.start()
    mock_dir = ASSETS_DIR / "mock"
    if not mock_dir.exists():
        return

    transient_states = {"processing", "cancel_requested"}
    rewritten = 0
    for status_path in mock_dir.glob("*/status.json"):
        try:
            data = read_json(status_path, default={}) or {}
            existing = str(data.get("status") or "").strip().lower()
            if existing not in transient_states:
                continue
            data["status"] = "abandoned"
            data["abandoned_at"] = int(time.time())
            data["abandoned_reason"] = (
                f"server restarted while workflow status was '{existing}'"
            )
            write_json_atomic(status_path, data)
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


def _require_workflow_id(workflow_id: object) -> str:
    try:
        return sanitize_storage_id(workflow_id, field_name="workflow_id")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _require_storage_id(value: object, field_name: str) -> str:
    try:
        return sanitize_storage_id(value, field_name=field_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _workflow_dir(workflow_id: str) -> Path:
    return safe_child_dir(ASSETS_DIR / "mock", workflow_id, field_name="workflow_id")


def _workflow_status_path(workflow_id: str) -> Path:
    return _workflow_dir(workflow_id) / "status.json"


def _workflow_outputs_path(workflow_id: str) -> Path:
    return _workflow_dir(workflow_id) / "outputs.json"


def _raise_if_cancelled(workflow_id: str, *, scope: str = "workflow") -> None:
    if not _is_cancelled(workflow_id):
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "WORKFLOW_CANCELLED",
            "workflow_id": workflow_id,
            "scope": scope,
            "message": "workflow cancellation requested",
        },
    )


def _patch_workflow_outputs(workflow_id: str, patch: dict) -> None:
    """Merge patch fields into the stored outputs.json for a workflow run."""
    path = _workflow_outputs_path(workflow_id)
    if not path.exists():
        return
    try:
        def merge(data):
            if not isinstance(data, dict):
                raise ValueError("workflow outputs must be a JSON object")
            nested = data.get("outputs")
            if isinstance(nested, dict):
                nested.update(patch)
            else:
                data.update(patch)
            return data

        update_json_atomic(path, merge)
    except Exception as e:
        print(f"[patch_workflow_outputs] failed to patch {workflow_id}: {e}")


def _merge_review_scene_item(
    workflow_id: str,
    run_id: str,
    scene_item: dict,
) -> dict:
    """Upsert one review scene against the latest on-disk outputs."""
    merged: dict = {}

    def update(document):
        if not isinstance(document, dict):
            raise ValueError("workflow outputs must be a JSON object")
        outputs = (
            document["outputs"]
            if isinstance(document.get("outputs"), dict)
            else document
        )
        current_review = outputs.get("image_review") or {}
        provider = str(
            current_review.get("provider")
            or (outputs.get("image_assets") or {}).get("provider")
            or _runner._image_provider_name()
        )
        latest_review = _runner._image_review.upsert_image_review_item(
            image_review=current_review,
            scene_review_item=scene_item,
            provider=provider,
        )
        storyboard_scenes = (outputs.get("storyboard") or {}).get("scenes") or []
        prior_assets = outputs.get("image_assets") or {}
        failed_ids = [
            str(value)
            for value in (prior_assets.get("failed_scene_ids") or [])
            if str(value) != str(scene_item.get("scene_id") or "")
        ]
        latest_assets = _runner.build_image_assets_from_selected_assets(
            run_id=run_id,
            image_review=latest_review,
            provider=provider,
            storyboard_scenes=storyboard_scenes,
            known_failed_scene_ids=failed_ids,
        )
        outputs["image_review"] = latest_review
        outputs["image_assets"] = latest_assets
        merged.update({"image_review": latest_review, "image_assets": latest_assets})
        return document

    update_json_atomic(_workflow_outputs_path(workflow_id), update)
    return merged


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
    write_json_atomic(_workflow_status_path(workflow_id), payload)
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
    req = dict(req)
    workflow_id = _require_workflow_id(
        req.get("workflow_id") or f"wf_{int(time.time()*1000)}"
    )
    req["workflow_id"] = workflow_id
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
        write_json_atomic(_workflow_outputs_path(workflow_id), outputs)
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
    workflow_id = _require_workflow_id(req.get("workflow_id"))
    scope = str(req.get("scope") or "workflow").strip().lower()

    # Candidate-image refresh happens after the main workflow status is
    # already completed. Still mark the cancellation registry so in-flight
    # /refresh-scene handlers can stop before persisting late results, but
    # do not rewrite status.json: story/storyboard outputs remain valid and
    # the frontend shows the paused refresh state from its own marker.
    if scope == "image_refresh":
        _request_cancel(workflow_id)
        return {
            "workflow_id": workflow_id,
            "status": "cancel_requested",
            "scope": scope,
        }

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


@app.post("/v1/workflow/cancel/clear")
def clear_workflow_cancel(req: dict = Body(...)):
    workflow_id = _require_workflow_id(req.get("workflow_id"))
    _clear_cancel(workflow_id)
    return {"workflow_id": workflow_id, "status": "cancel_cleared"}


@app.get("/v1/workflow/status/{workflow_id}")
def get_workflow_status(workflow_id: str):
    workflow_id = _require_workflow_id(workflow_id)
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
    workflow_id = _require_workflow_id(workflow_id)
    outputs_path = _workflow_outputs_path(workflow_id)
    if not outputs_path.exists():
        raise HTTPException(status_code=404, detail=f"workflow results not found: {workflow_id}")
    try:
        outputs = read_json(outputs_path)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"failed to read workflow results: {e}")
    return outputs


@app.post("/v1/image-review/select", response_model=ImageReviewSelectResponse)
def select_image_review_asset(req: ImageReviewSelectRequest):
    print("[image-review] selection request received", req.workflow_id, req.scene_id)
    workflow_id = _require_workflow_id(req.workflow_id)
    try:
        result = _runner.update_image_review_selection(
            workflow_id=workflow_id,
            session_id=req.session_id,
            run_id=req.run_id,
            scene_id=req.scene_id,
            selected_asset_ref=req.selected_asset_ref,
            image_review=req.image_review,
            storyboard=req.storyboard,
            workflow_input=req.workflow_input,
            video_provider=req.video_provider,
        )
        selected_items = (result.get("image_review") or {}).get("selected_assets") or []
        selected_item = next(
            (
                item
                for item in selected_items
                if isinstance(item, dict)
                and str(item.get("scene_id") or "") == str(req.scene_id or "")
            ),
            None,
        )
        if selected_item:
            persisted = _merge_review_scene_item(
                workflow_id, req.run_id, selected_item
            )
            result.update(persisted)
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
    workflow_id = _require_workflow_id(req.workflow_id)
    try:
        result = _runner.rerender_final_video(
            workflow_id=workflow_id,
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
        _patch_workflow_outputs(workflow_id, {
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
    workflow_id = _require_workflow_id(req.workflow_id)
    _raise_if_cancelled(workflow_id, scope="image_refresh")
    try:
        result = _runner.refresh_image_review(
            workflow_id=workflow_id,
            session_id=req.session_id,
            run_id=req.run_id,
            storyboard=req.storyboard,
            workflow_input=req.workflow_input,
            image_review=req.image_review,
            character_manifest=getattr(req, "character_manifest", None),
            image_prompts=getattr(req, "image_prompts", None),
            video_provider=req.video_provider,
        )
        _raise_if_cancelled(workflow_id, scope="image_refresh")
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
    except HTTPException:
        raise
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
    workflow_id = _require_workflow_id(req.workflow_id)
    _raise_if_cancelled(workflow_id, scope="image_refresh")
    try:
        result = _runner.refresh_image_review_scene(
            workflow_id=workflow_id,
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
        _raise_if_cancelled(workflow_id, scope="image_refresh")
        print("[image-review] refresh-scene completed", req.run_id, req.scene_id)

        # Merge from the files under the shared outputs lock. Never persist the
        # request's stale image_review snapshot over scenes completed meanwhile.
        reconciled = _image_refresh_coordinator.reconcile(
            workflow_id, req.run_id, req.scene_id
        )
        if reconciled:
            result["image_review"] = reconciled["image_review"]
            result["image_assets"] = reconciled["image_assets"]
            result["scene_review_item"] = reconciled["scene_review_item"]

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
    except HTTPException:
        raise
    except Exception as e:
        print("[image-review] refresh-scene runtime error", repr(e))
        # Two failure semantics, discriminated by whether the current
        # scene was already in image_review.selected_assets:
        #
        #   had_prior_success=True (重新生成 case):
        #     The scene already had a valid generated image. The retry
        #     blew up but the workflow state is *unchanged* — old
        #     selection still wins. Do NOT strip selected_assets, do
        #     NOT mark the scene failed, do NOT patch outputs.json.
        #     The FE shows a non-blocking toast and the pipeline keeps
        #     its assets-ready state.
        #
        #   had_prior_success=False (重试该场景 case):
        #     The scene had no valid image. Persist this failure so the
        #     FE's failure-aware UI engages:
        #       1. add current scene to known_failed_scene_ids so the
        #          helper emits a `failed` placeholder
        #       2. patch image_assets to disk
        #       3. embed rebuilt assets in the 502 detail so the FE
        #          updates in-memory state without a reload
        current_scene = str(req.scene_id or "").strip()
        stored_document = read_json(_workflow_outputs_path(workflow_id), default={}) or {}
        stored_outputs = (
            stored_document.get("outputs")
            if isinstance(stored_document, dict)
            and isinstance(stored_document.get("outputs"), dict)
            else stored_document
        )
        stored_review = (
            stored_outputs.get("image_review")
            if isinstance(stored_outputs, dict)
            else {}
        ) or {}
        prior_selected_raw = stored_review.get("selected_assets") or []
        had_prior_success = bool(current_scene) and isinstance(
            prior_selected_raw, list
        ) and any(
            isinstance(s, dict)
            and str(s.get("scene_id") or "").strip() == current_scene
            for s in prior_selected_raw
        )

        rebuilt_image_assets = None
        if not had_prior_success:
            try:
                failed_state = _image_refresh_coordinator.mark_failed(
                    workflow_id, req.run_id, current_scene
                )
                rebuilt_image_assets = failed_state["image_assets"]
            except Exception as persist_err:
                print(
                    "[image-review] failed to persist failure",
                    repr(persist_err),
                )

        detail = _refresh_scene_error_detail(req, e)
        if rebuilt_image_assets is not None:
            detail["image_assets"] = rebuilt_image_assets
        raise HTTPException(
            status_code=502,
            detail=detail,
        ) from e


@app.post(
    "/v1/image-review/refresh-scene-task",
    response_model=ImageReviewRefreshSceneTaskResponse,
    status_code=202,
)
def create_image_review_scene_task(req: ImageReviewRefreshSceneTaskRequest):
    workflow_id = _require_workflow_id(req.workflow_id)
    run_id = _require_storage_id(req.run_id, "run_id")
    scene_id = _require_storage_id(req.scene_id, "scene_id")
    _image_refresh_tasks.start()
    payload = req.model_dump(exclude={"retry_failed"})
    payload["workflow_id"] = workflow_id
    payload["run_id"] = run_id
    payload["scene_id"] = scene_id
    payload["force_regenerate"] = bool(req.retry_failed)
    try:
        task, _created = _image_refresh_tasks.submit(
            payload, retry_failed=req.retry_failed
        )
        return ImageReviewRefreshSceneTaskResponse(**task)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get(
    "/v1/image-review/refresh-scene-tasks",
    response_model=ImageReviewRefreshTaskBatchResponse,
)
def list_image_review_scene_tasks(workflow_id: str, run_id: str):
    started_at = time.perf_counter()
    normalized_workflow_id = _require_workflow_id(workflow_id)
    normalized_run_id = _require_storage_id(run_id, "run_id")
    tasks = _image_refresh_tasks.list_for_run(
        normalized_workflow_id, normalized_run_id
    )
    response = ImageReviewRefreshTaskBatchResponse(
        workflow_id=normalized_workflow_id,
        run_id=normalized_run_id,
        found=bool(tasks),
        tasks=tasks,
    )
    logger.info(
        "image refresh batch endpoint duration_ms=%.2f task_count=%d",
        (time.perf_counter() - started_at) * 1000,
        len(tasks),
    )
    return response


@app.get(
    "/v1/image-review/refresh-scene-task",
    response_model=ImageReviewRefreshSceneTaskResponse,
)
def recover_image_review_scene_task(
    workflow_id: str, run_id: str, scene_id: str
):
    normalized_workflow_id = _require_workflow_id(workflow_id)
    run_id = _require_storage_id(run_id, "run_id")
    scene_id = _require_storage_id(scene_id, "scene_id")
    _image_refresh_tasks.start()
    task = _image_refresh_tasks.recover_status(
        normalized_workflow_id, run_id, scene_id
    )
    if task is None:
        raise HTTPException(status_code=404, detail="image refresh task not found")
    return ImageReviewRefreshSceneTaskResponse(**task)


@app.get(
    "/v1/image-review/refresh-scene-task/{task_id}",
    response_model=ImageReviewRefreshSceneTaskResponse,
)
def get_image_review_scene_task(task_id: str):
    _image_refresh_tasks.start()
    task = _image_refresh_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"image refresh task not found: {task_id}")
    return ImageReviewRefreshSceneTaskResponse(**task)
