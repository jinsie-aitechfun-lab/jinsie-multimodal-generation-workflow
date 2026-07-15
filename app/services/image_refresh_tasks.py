from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
import traceback
from pathlib import Path
from queue import Queue
from typing import Any

from app.services.atomic_json_store import read_json, update_json_atomic, write_json_atomic
from app.services.storage_ids import safe_child_dir


logger = logging.getLogger(__name__)


TERMINAL_TASK_STATES = {"succeeded", "failed"}


def _outputs_container(document: dict[str, Any]) -> dict[str, Any]:
    nested = document.get("outputs")
    return nested if isinstance(nested, dict) else document


class ImageRefreshCoordinator:
    """Reconcile generated files and merge one scene into authoritative outputs."""

    def __init__(self, assets_dir: Path, runner: Any) -> None:
        self.assets_dir = assets_dir
        self.mock_root = assets_dir / "mock"
        self.runner = runner

    def outputs_path(self, workflow_id: str) -> Path:
        return safe_child_dir(
            self.mock_root, workflow_id, field_name="workflow_id"
        ) / "outputs.json"

    def candidate_paths(self, run_id: str, scene_id: str) -> list[Path]:
        run_dir = safe_child_dir(
            self.mock_root / "image", run_id, field_name="run_id"
        )
        return [
            run_dir / f"{scene_id}__candidate_a.png",
            run_dir / f"{scene_id}__candidate_b.png",
        ]

    def _candidate_refs(self, run_id: str, scene_id: str) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for path in self.candidate_paths(run_id, scene_id):
            if not path.is_file() or path.stat().st_size <= 0:
                return []
            relative = f"assets/mock/image/{run_id}/{path.name}"
            refs.append(
                {
                    "scene_id": scene_id,
                    "file_name": path.name,
                    "relative_path": relative,
                    "public_url": f"/{relative}",
                    "mime_type": "image/png",
                    "provider": "reconciled_existing_file",
                    "version": str(path.stat().st_mtime_ns),
                }
            )
        return refs

    @staticmethod
    def _same_asset(left: dict[str, Any], right: dict[str, Any]) -> bool:
        for key in ("relative_path", "public_url", "file_name"):
            if left.get(key) and left.get(key) == right.get(key):
                return True
        return False

    def reconcile(self, workflow_id: str, run_id: str, scene_id: str) -> dict[str, Any] | None:
        refs = self._candidate_refs(run_id, scene_id)
        if len(refs) != 2:
            return None

        path = self.outputs_path(workflow_id)
        if not path.exists():
            return None

        result: dict[str, Any] = {}

        def merge(document: Any) -> Any:
            if not isinstance(document, dict):
                raise ValueError("workflow outputs must be a JSON object")
            outputs = _outputs_container(document)
            storyboard = outputs.get("storyboard") or {}
            scenes = storyboard.get("scenes") or []
            scene = next(
                (
                    item
                    for item in scenes
                    if isinstance(item, dict)
                    and str(item.get("scene_id") or "").strip() == scene_id
                ),
                None,
            )
            if scene is None:
                raise ValueError(f"scene_id not found in stored storyboard: {scene_id}")

            review = outputs.get("image_review") or {}
            selected = review.get("selected_assets") or []
            existing = next(
                (
                    item
                    for item in selected
                    if isinstance(item, dict)
                    and str(item.get("scene_id") or "").strip() == scene_id
                ),
                None,
            )
            selected_ref = refs[0]
            if isinstance(existing, dict):
                old_selected = existing.get("selected_asset_ref")
                if isinstance(old_selected, dict):
                    selected_ref = next(
                        (ref for ref in refs if self._same_asset(old_selected, ref)),
                        refs[0],
                    )

            asset = {
                "scene_id": scene_id,
                "scene_title": str(scene.get("scene_title") or scene_id),
                "characters": (existing or {}).get("characters") or scene.get("characters") or [],
                "character_ids": (existing or {}).get("character_ids") or [],
                "prompt": str((existing or {}).get("prompt") or ""),
                "file_name": selected_ref["file_name"],
                "relative_path": selected_ref["relative_path"],
                "public_url": selected_ref["public_url"],
                "mime_type": "image/png",
                "status": "generated",
                "selected_asset_ref": selected_ref,
                "candidate_asset_refs": refs,
            }
            if isinstance(existing, dict):
                item = dict(existing)
                item.update(
                    {
                        "selected_asset_ref": selected_ref,
                        "candidate_asset_refs": refs,
                        "review_status": existing.get("review_status") or "auto_selected",
                    }
                )
            else:
                item = self.runner._image_review.build_image_review_item_from_asset(
                    asset, provider="reconciled_existing_file"
                )

            latest_review = self.runner._image_review.upsert_image_review_item(
                image_review=review,
                scene_review_item=item,
                provider=str(review.get("provider") or "reconciled_existing_file"),
            )
            prior_assets = outputs.get("image_assets") or {}
            failed_ids = [
                str(value)
                for value in (prior_assets.get("failed_scene_ids") or [])
                if str(value) != scene_id
            ]
            latest_assets = self.runner.build_image_assets_from_selected_assets(
                run_id=run_id,
                image_review=latest_review,
                provider=str(prior_assets.get("provider") or "reconciled_existing_file"),
                storyboard_scenes=scenes,
                known_failed_scene_ids=failed_ids,
            )
            outputs["image_review"] = latest_review
            outputs["image_assets"] = latest_assets
            result.update(
                {
                    "scene_id": scene_id,
                    "scene_review_item": item,
                    "image_review": latest_review,
                    "image_assets": latest_assets,
                    "reconciled": True,
                }
            )
            return document

        update_json_atomic(path, merge)
        return result

    def generate_and_merge(self, payload: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(payload["workflow_id"])
        run_id = str(payload["run_id"])
        scene_id = str(payload["scene_id"])

        reconciled = self.reconcile(workflow_id, run_id, scene_id)
        if reconciled is not None:
            return reconciled

        stored = read_json(self.outputs_path(workflow_id), default={}) or {}
        outputs = _outputs_container(stored) if isinstance(stored, dict) else {}
        latest_review = outputs.get("image_review") or payload.get("image_review") or {}
        latest_storyboard = outputs.get("storyboard") or payload.get("storyboard") or {}

        generated = self.runner.refresh_image_review_scene(
            workflow_id=workflow_id,
            session_id=payload.get("session_id"),
            run_id=run_id,
            scene_id=scene_id,
            storyboard=latest_storyboard,
            workflow_input=payload.get("workflow_input") or {},
            image_review=latest_review,
            character_manifest=outputs.get("character_manifest") or payload.get("character_manifest") or {},
            image_prompts=outputs.get("image_prompts") or payload.get("image_prompts") or {},
            video_provider=str(payload.get("video_provider") or "mock"),
            preserve_seed=bool(payload.get("preserve_seed")),
            known_failed_scene_ids=list(payload.get("known_failed_scene_ids") or []),
        )

        def invalidate_video(document: Any) -> Any:
            if isinstance(document, dict):
                _outputs_container(document).pop("final_video", None)
            return document

        update_json_atomic(self.outputs_path(workflow_id), invalidate_video)

        # Files are authoritative. Reconcile under the shared outputs lock so
        # a late scene can only upsert itself, never replace another scene.
        merged = self.reconcile(workflow_id, run_id, scene_id)
        if merged is None:
            raise RuntimeError("candidate files missing after provider succeeded")
        return merged

    def mark_failed(self, workflow_id: str, run_id: str, scene_id: str) -> dict[str, Any]:
        """Persist one terminal failure without replacing successful scenes."""
        path = self.outputs_path(workflow_id)
        result: dict[str, Any] = {}

        def merge(document: Any) -> Any:
            if not isinstance(document, dict):
                raise ValueError("workflow outputs must be a JSON object")
            outputs = _outputs_container(document)
            review = outputs.get("image_review") or {}
            storyboard = outputs.get("storyboard") or {}
            scenes = storyboard.get("scenes") or []
            prior_assets = outputs.get("image_assets") or {}
            failed_ids = {
                str(value)
                for value in (prior_assets.get("failed_scene_ids") or [])
                if str(value)
            }
            failed_ids.add(scene_id)
            latest_assets = self.runner.build_image_assets_from_selected_assets(
                run_id=run_id,
                image_review=review,
                provider=str(prior_assets.get("provider") or self.runner._image_provider_name()),
                storyboard_scenes=scenes,
                known_failed_scene_ids=sorted(failed_ids),
            )
            outputs["image_assets"] = latest_assets
            result.update({"image_review": review, "image_assets": latest_assets})
            return document

        update_json_atomic(path, merge)
        return result


class ImageRefreshTaskManager:
    def __init__(self, assets_dir: Path, coordinator: ImageRefreshCoordinator) -> None:
        self.assets_dir = assets_dir
        self.mock_root = assets_dir / "mock"
        self.coordinator = coordinator
        self.queue: Queue[str] = Queue()
        self.tasks: dict[str, Path] = {}
        self.task_ids_by_run: dict[tuple[str, str], set[str]] = {}
        self.guard = threading.RLock()
        self.started = False
        try:
            configured_concurrency = int(
                os.getenv("IMAGE_TASK_CONCURRENCY", "1") or "1"
            )
        except ValueError:
            configured_concurrency = 1
        self.concurrency = max(1, configured_concurrency)

    @staticmethod
    def task_id_for(workflow_id: str, run_id: str, scene_id: str) -> str:
        digest = hashlib.sha256(
            f"{workflow_id}\0{run_id}\0{scene_id}".encode("utf-8")
        ).hexdigest()[:24]
        return f"img_{digest}"

    def _task_path(self, workflow_id: str, task_id: str) -> Path:
        workflow_dir = safe_child_dir(
            self.mock_root, workflow_id, field_name="workflow_id"
        )
        return workflow_dir / "image_refresh_tasks" / f"{task_id}.json"

    def _register_task(self, task_id: str, path: Path, workflow_id: str, run_id: str) -> None:
        self.tasks[task_id] = path
        self.task_ids_by_run.setdefault((workflow_id, run_id), set()).add(task_id)

    def start(self) -> None:
        with self.guard:
            if self.started:
                return
            self.started = True
            for path in self.mock_root.glob("*/image_refresh_tasks/*.json"):
                task = read_json(path, default={}) or {}
                task_id = str(task.get("task_id") or "")
                if not task_id:
                    continue
                self._register_task(
                    task_id,
                    path,
                    str(task.get("workflow_id") or ""),
                    str(task.get("run_id") or ""),
                )
                if str(task.get("status") or "") in {"queued", "running"}:
                    recovered = self.coordinator.reconcile(
                        str(task.get("workflow_id") or ""),
                        str(task.get("run_id") or ""),
                        str(task.get("scene_id") or ""),
                    )
                    task["status"] = "succeeded" if recovered else "failed"
                    task["result"] = recovered or {}
                    task["error"] = "server restarted before task completion" if not recovered else ""
                    task["updated_at"] = int(time.time())
                    write_json_atomic(path, task)

            for index in range(self.concurrency):
                threading.Thread(
                    target=self._worker,
                    daemon=True,
                    name=f"ImageRefreshWorker-{index + 1}",
                ).start()

    def submit(self, payload: dict[str, Any], *, retry_failed: bool = False) -> tuple[dict[str, Any], bool]:
        workflow_id = str(payload["workflow_id"])
        run_id = str(payload["run_id"])
        scene_id = str(payload["scene_id"])
        task_id = self.task_id_for(workflow_id, run_id, scene_id)
        path = self._task_path(workflow_id, task_id)
        self._register_task(task_id, path, workflow_id, run_id)

        reconciled = self.coordinator.reconcile(workflow_id, run_id, scene_id)
        if reconciled is not None:
            task = {
                "task_id": task_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "scene_id": scene_id,
                "status": "succeeded",
                "result": reconciled,
                "error": "",
                "updated_at": int(time.time()),
            }
            write_json_atomic(path, task)
            return task, False

        with self.guard:
            existing = read_json(path, default=None)
            if isinstance(existing, dict):
                status = str(existing.get("status") or "")
                if status in {"queued", "running"}:
                    return existing, False
                if status == "succeeded":
                    existing["status"] = "failed"
                    existing["error"] = "task metadata succeeded but candidate files are missing"
                    existing["updated_at"] = int(time.time())
                    write_json_atomic(path, existing)
                    status = "failed"
                if status == "failed" and not retry_failed:
                    return existing, False

            now = int(time.time())
            task = {
                "task_id": task_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "scene_id": scene_id,
                "status": "queued",
                "payload": payload,
                "result": {},
                "error": "",
                "created_at": (existing or {}).get("created_at", now) if isinstance(existing, dict) else now,
                "updated_at": now,
            }
            write_json_atomic(path, task)
            self.queue.put(task_id)
            return task, True

    def get(self, task_id: str) -> dict[str, Any] | None:
        path = self.tasks.get(task_id)
        if path is None:
            return None
        task = read_json(path, default=None)
        if not isinstance(task, dict):
            return None
        return task

    def list_for_run(self, workflow_id: str, run_id: str) -> list[dict[str, Any]]:
        """Read all registered task summaries for one workflow/run without side effects."""
        started_at = time.perf_counter()
        with self.guard:
            task_ids = tuple(self.task_ids_by_run.get((workflow_id, run_id), ()))
            task_paths = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]

        tasks: list[dict[str, Any]] = []
        for path in task_paths:
            task = read_json(path, default=None)
            if not isinstance(task, dict):
                continue
            if str(task.get("workflow_id") or "") != workflow_id:
                continue
            if str(task.get("run_id") or "") != run_id:
                continue
            tasks.append(
                {
                    "found": True,
                    "task_id": str(task.get("task_id") or ""),
                    "workflow_id": workflow_id,
                    "run_id": run_id,
                    "scene_id": str(task.get("scene_id") or ""),
                    "status": str(task.get("status") or ""),
                    "error": str(task.get("error") or ""),
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                }
            )

        tasks.sort(key=lambda item: str(item.get("scene_id") or ""))
        logger.info(
            "image refresh batch task read duration_ms=%.2f task_count=%d",
            (time.perf_counter() - started_at) * 1000,
            len(tasks),
        )
        return tasks

    def recover_status(
        self, workflow_id: str, run_id: str, scene_id: str
    ) -> dict[str, Any] | None:
        task_id = self.task_id_for(workflow_id, run_id, scene_id)
        path = self._task_path(workflow_id, task_id)
        self._register_task(task_id, path, workflow_id, run_id)
        reconciled = self.coordinator.reconcile(workflow_id, run_id, scene_id)
        if reconciled is not None:
            task = {
                "task_id": task_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "scene_id": scene_id,
                "status": "succeeded",
                "result": reconciled,
                "error": "",
                "updated_at": int(time.time()),
            }
            write_json_atomic(path, task)
            return task
        existing = self.get(task_id)
        if existing and str(existing.get("status") or "") == "succeeded":
            existing["status"] = "failed"
            existing["error"] = "task metadata succeeded but candidate files are missing"
            existing["updated_at"] = int(time.time())
            write_json_atomic(path, existing)
        return existing

    def _worker(self) -> None:
        while True:
            task_id = self.queue.get()
            try:
                path = self.tasks[task_id]
                task = read_json(path, default={}) or {}
                if str(task.get("status") or "") != "queued":
                    continue
                task["status"] = "running"
                task["updated_at"] = int(time.time())
                write_json_atomic(path, task)
                try:
                    result = self.coordinator.generate_and_merge(task.get("payload") or {})
                    task["status"] = "succeeded"
                    task["result"] = result
                    task["error"] = ""
                except Exception as error:
                    recovered = self.coordinator.reconcile(
                        str(task.get("workflow_id") or ""),
                        str(task.get("run_id") or ""),
                        str(task.get("scene_id") or ""),
                    )
                    if recovered is not None:
                        task["status"] = "succeeded"
                        task["result"] = recovered
                        task["error"] = ""
                    else:
                        task["status"] = "failed"
                        task["error"] = str(error) or error.__class__.__name__
                        self.coordinator.mark_failed(
                            str(task.get("workflow_id") or ""),
                            str(task.get("run_id") or ""),
                            str(task.get("scene_id") or ""),
                        )
                        traceback.print_exc()
                task["updated_at"] = int(time.time())
                task.pop("payload", None)
                write_json_atomic(path, task)
            finally:
                self.queue.task_done()
