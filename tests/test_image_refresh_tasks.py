from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from app.services.image_refresh_tasks import (
    ImageRefreshCoordinator,
    ImageRefreshTaskManager,
)


class _FakeReview:
    def build_image_review_item_from_asset(self, asset, provider):
        return {
            "scene_id": asset["scene_id"],
            "scene_title": asset["scene_title"],
            "review_status": "auto_selected",
            "selection_mode": "default_first_pass",
            "selection_source": "default_auto_selection",
            "selection_reason": "test",
            "selected_asset_ref": asset["selected_asset_ref"],
            "candidate_asset_refs": asset["candidate_asset_refs"],
            "characters": asset.get("characters", []),
            "character_ids": asset.get("character_ids", []),
            "prompt": asset.get("prompt", ""),
        }

    def upsert_image_review_item(self, image_review, scene_review_item, provider):
        items = [
            dict(item)
            for item in image_review.get("selected_assets", [])
            if item.get("scene_id") != scene_review_item["scene_id"]
        ]
        items.append(dict(scene_review_item))
        return {
            **image_review,
            "enabled": True,
            "mode": "selection_contract",
            "provider": provider,
            "selected_assets": items,
            "selected_count": len(items),
            "asset_count": len(items),
        }


class _FakeRunner:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self._image_review = _FakeReview()
        self.provider_calls = 0
        self.provider_lock = threading.Lock()

    def _image_provider_name(self):
        return "mock"

    def build_image_assets_from_selected_assets(
        self,
        *,
        run_id,
        image_review,
        provider,
        storyboard_scenes,
        known_failed_scene_ids=None,
    ):
        selected = image_review.get("selected_assets", [])
        selected_ids = {item["scene_id"] for item in selected}
        failed = [
            scene_id
            for scene_id in (known_failed_scene_ids or [])
            if scene_id not in selected_ids
        ]
        assets = []
        for item in selected:
            selected_ref = item["selected_asset_ref"]
            assets.append(
                {
                    "scene_id": item["scene_id"],
                    "scene_title": item.get("scene_title", ""),
                    "status": "generated",
                    "selected_asset_ref": selected_ref,
                    "candidate_asset_refs": item["candidate_asset_refs"],
                    **selected_ref,
                }
            )
        for scene_id in failed:
            assets.append({"scene_id": scene_id, "status": "failed"})
        return {
            "run_id": run_id,
            "provider": provider,
            "status": "completed" if not failed else "partial_failure",
            "assets": assets,
            "asset_count": len(assets),
            "generated_count": len(selected),
            "failed_count": len(failed),
            "failed_scene_ids": failed,
        }

    def refresh_image_review_scene(self, **kwargs):
        with self.provider_lock:
            self.provider_calls += 1
            generation = self.provider_calls
        time.sleep(0.03)
        run_id = kwargs["run_id"]
        scene_id = kwargs["scene_id"]
        run_dir = self.assets_dir / "mock" / "image" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        refs = []
        for suffix in ("candidate_a", "candidate_b"):
            file_name = f"{scene_id}__{suffix}.png"
            relative_path = f"assets/mock/image/{run_id}/{file_name}"
            (run_dir / file_name).write_bytes(
                f"png-generation-{generation}-{suffix}".encode()
            )
            refs.append(
                {
                    "scene_id": scene_id,
                    "file_name": file_name,
                    "relative_path": relative_path,
                    "public_url": f"/{relative_path}",
                    "mime_type": "image/png",
                    "auto_filter_score": 10 if suffix == "candidate_a" else 90,
                }
            )
        selected_ref = refs[1]
        return {
            "scene_id": scene_id,
            "scene_review_item": {
                "scene_id": scene_id,
                "scene_title": scene_id,
                "review_status": "auto_selected",
                "selection_mode": "auto_filter",
                "selection_source": "auto_filter",
                "selection_reason": "candidate_b scored higher",
                "selected_asset_ref": selected_ref,
                "candidate_asset_refs": refs,
                "candidate_scores": [
                    {"file_name": refs[1]["file_name"], "score": 90},
                    {"file_name": refs[0]["file_name"], "score": 10},
                ],
            },
        }


class ImageRefreshReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.assets_dir = Path(self.temp.name) / "assets"
        self.workflow_id = "workflow_test"
        self.run_id = "run_test"
        self.workflow_dir = self.assets_dir / "mock" / self.workflow_id
        self.workflow_dir.mkdir(parents=True)
        self.scenes = [
            {"scene_id": f"scene_{index:02d}", "scene_title": f"Scene {index}"}
            for index in range(1, 7)
        ]
        self.outputs_path = self.workflow_dir / "outputs.json"
        self.outputs_path.write_text(
            json.dumps(
                {
                    "workflow_id": self.workflow_id,
                    "run_id": self.run_id,
                    "outputs": {
                        "storyboard": {"scenes": self.scenes},
                        "image_review": {"selected_assets": []},
                        "image_assets": {"assets": []},
                    },
                }
            ),
            encoding="utf-8",
        )
        self.runner = _FakeRunner(self.assets_dir)
        self.coordinator = ImageRefreshCoordinator(self.assets_dir, self.runner)

    def tearDown(self):
        self.temp.cleanup()

    def _write_candidates(self, scene_id: str):
        run_dir = self.assets_dir / "mock" / "image" / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        for suffix in ("candidate_a", "candidate_b"):
            (run_dir / f"{scene_id}__{suffix}.png").write_bytes(b"png")

    def test_six_out_of_order_reconciles_do_not_lose_scenes(self):
        for scene in self.scenes:
            self._write_candidates(scene["scene_id"])

        threads = [
            threading.Thread(
                target=self.coordinator.reconcile,
                args=(self.workflow_id, self.run_id, scene["scene_id"]),
            )
            for scene in reversed(self.scenes)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        document = json.loads(self.outputs_path.read_text(encoding="utf-8"))
        review = document["outputs"]["image_review"]
        scene_ids = [item["scene_id"] for item in review["selected_assets"]]
        self.assertEqual(6, len(scene_ids))
        self.assertEqual(6, len(set(scene_ids)))
        self.assertEqual(0, self.runner.provider_calls)

    def test_existing_files_restore_metadata_without_provider(self):
        self._write_candidates("scene_05")
        result = self.coordinator.reconcile(
            self.workflow_id, self.run_id, "scene_05"
        )
        self.assertIsNotNone(result)
        self.assertEqual(0, self.runner.provider_calls)
        self.assertEqual(1, result["image_review"]["selected_count"])

    def test_duplicate_submit_reuses_task_and_calls_provider_once(self):
        old = os.environ.get("IMAGE_TASK_CONCURRENCY")
        os.environ["IMAGE_TASK_CONCURRENCY"] = "1"
        try:
            manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
            manager.start()
            payload = {
                "workflow_id": self.workflow_id,
                "run_id": self.run_id,
                "scene_id": "scene_01",
                "storyboard": {"scenes": self.scenes},
                "workflow_input": {},
                "image_review": {},
            }
            first, _ = manager.submit(payload)
            second, _ = manager.submit(payload)
            self.assertEqual(first["task_id"], second["task_id"])

            deadline = time.time() + 2
            task = manager.get(first["task_id"])
            while task and task["status"] not in {"succeeded", "failed"}:
                self.assertLess(time.time(), deadline)
                time.sleep(0.01)
                task = manager.get(first["task_id"])
            self.assertEqual("succeeded", task["status"])
            third, _ = manager.submit(payload)
            self.assertEqual(first["task_id"], third["task_id"])
            self.assertEqual(1, self.runner.provider_calls)
        finally:
            if old is None:
                os.environ.pop("IMAGE_TASK_CONCURRENCY", None)
            else:
                os.environ["IMAGE_TASK_CONCURRENCY"] = old

    def test_batch_status_read_is_lightweight_and_does_not_reconcile(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        task_id = manager.task_id_for(
            self.workflow_id, self.run_id, "scene_01"
        )
        task_path = manager._task_path(self.workflow_id, task_id)
        task_path.parent.mkdir(parents=True, exist_ok=True)
        task = {
            "task_id": task_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "scene_id": "scene_01",
            "status": "succeeded",
            "result": {"large": "payload is intentionally omitted"},
            "error": "",
            "updated_at": 123,
        }
        task_path.write_text(json.dumps(task), encoding="utf-8")
        manager._register_task(task_id, task_path, self.workflow_id, self.run_id)
        outputs_before = self.outputs_path.read_bytes()
        task_before = task_path.read_bytes()

        original_reconcile = self.coordinator.reconcile
        self.coordinator.reconcile = lambda *args, **kwargs: self.fail(
            "batch status read must not reconcile"
        )
        try:
            statuses = manager.list_for_run(self.workflow_id, self.run_id)
        finally:
            self.coordinator.reconcile = original_reconcile

        self.assertEqual(1, len(statuses))
        self.assertEqual("scene_01", statuses[0]["scene_id"])
        self.assertNotIn("result", statuses[0])
        self.assertEqual(outputs_before, self.outputs_path.read_bytes())
        self.assertEqual(task_before, task_path.read_bytes())

    def test_single_task_get_is_read_only_after_success(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        task_id = manager.task_id_for(
            self.workflow_id, self.run_id, "scene_02"
        )
        task_path = manager._task_path(self.workflow_id, task_id)
        task_path.parent.mkdir(parents=True, exist_ok=True)
        task_path.write_text(
            json.dumps(
                {
                    "task_id": task_id,
                    "workflow_id": self.workflow_id,
                    "run_id": self.run_id,
                    "scene_id": "scene_02",
                    "status": "succeeded",
                    "result": {},
                    "error": "",
                    "updated_at": 456,
                }
            ),
            encoding="utf-8",
        )
        manager.tasks[task_id] = task_path
        outputs_before = self.outputs_path.read_bytes()
        task_before = task_path.read_bytes()

        original_reconcile = self.coordinator.reconcile
        self.coordinator.reconcile = lambda *args, **kwargs: self.fail(
            "ordinary task GET must not reconcile"
        )
        try:
            task = manager.get(task_id)
        finally:
            self.coordinator.reconcile = original_reconcile

        self.assertEqual("succeeded", task["status"])
        self.assertEqual(outputs_before, self.outputs_path.read_bytes())
        self.assertEqual(task_before, task_path.read_bytes())

    def _task_payload(self, scene_id: str):
        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "scene_id": scene_id,
            "storyboard": {"scenes": self.scenes},
            "workflow_input": {},
            "image_review": {},
        }

    def _wait_for_terminal(self, manager, task_id):
        deadline = time.time() + 2
        task = manager.get(task_id)
        while task and task["status"] not in {"succeeded", "failed"}:
            self.assertLess(time.time(), deadline)
            time.sleep(0.01)
            task = manager.get(task_id)
        return task

    def test_explicit_refresh_generates_different_candidate_files(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        manager.start()
        payload = self._task_payload("scene_01")
        first, _ = manager.submit(payload)
        first = self._wait_for_terminal(manager, first["task_id"])
        self.assertEqual("succeeded", first["status"])
        candidate_path = (
            self.assets_dir
            / "mock"
            / "image"
            / self.run_id
            / "scene_01__candidate_a.png"
        )
        first_bytes = candidate_path.read_bytes()

        regenerated, created = manager.submit(
            {**payload, "force_regenerate": True},
            retry_failed=True,
        )
        self.assertTrue(created)
        regenerated = self._wait_for_terminal(manager, regenerated["task_id"])

        self.assertEqual("succeeded", regenerated["status"])
        self.assertEqual(2, self.runner.provider_calls)
        self.assertNotEqual(first_bytes, candidate_path.read_bytes())

    def test_generated_selector_choice_survives_authoritative_reconcile(self):
        result = self.coordinator.generate_and_merge(
            {
                **self._task_payload("scene_02"),
                "force_regenerate": True,
            }
        )

        selected = next(
            item
            for item in result["image_review"]["selected_assets"]
            if item["scene_id"] == "scene_02"
        )
        self.assertEqual(
            "scene_02__candidate_b.png",
            selected["selected_asset_ref"]["file_name"],
        )
        self.assertEqual("auto_filter", selected["selection_source"])
        self.assertEqual(90, selected["candidate_scores"][0]["score"])

    def test_persistent_index_survives_empty_memory_cache_and_new_manager(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        for scene in self.scenes:
            manager.submit(self._task_payload(scene["scene_id"]))

        manager.tasks.clear()
        manager.task_ids_by_run.clear()
        statuses = manager.list_for_run(self.workflow_id, self.run_id)
        self.assertEqual(6, len(statuses))

        replacement = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        replacement_statuses = replacement.list_for_run(
            self.workflow_id, self.run_id
        )
        self.assertEqual(6, len(replacement_statuses))

    def test_missing_index_recovers_only_current_workflow_task_directory(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        for scene in self.scenes[:2]:
            manager.submit(self._task_payload(scene["scene_id"]))
        manager._task_index_path(self.workflow_id).unlink()
        manager.tasks.clear()
        manager.task_ids_by_run.clear()

        statuses = manager.list_for_run(self.workflow_id, self.run_id)

        self.assertEqual(
            ["scene_01", "scene_02"],
            [item["scene_id"] for item in statuses],
        )
        self.assertFalse(manager._task_index_path(self.workflow_id).exists())

    def test_corrupt_indexed_task_is_reported_without_failing_batch(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        task, _ = manager.submit(self._task_payload("scene_01"))
        manager._task_path(self.workflow_id, task["task_id"]).write_text(
            "{not-json", encoding="utf-8"
        )

        statuses = manager.list_for_run(self.workflow_id, self.run_id)

        self.assertEqual(1, len(statuses))
        self.assertFalse(statuses[0]["found"])
        self.assertIsNone(statuses[0]["status"])
        self.assertIn("corrupt", statuses[0]["error"])

    def test_partial_index_is_completed_from_current_workflow_task_files(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        first, _ = manager.submit(self._task_payload("scene_01"))
        manager.submit(self._task_payload("scene_02"))
        manager._task_index_path(self.workflow_id).write_text(
            json.dumps(
                {
                    "workflow_id": self.workflow_id,
                    "runs": {self.run_id: {"scene_01": first["task_id"]}},
                }
            ),
            encoding="utf-8",
        )

        statuses = manager.list_for_run(self.workflow_id, self.run_id)

        self.assertEqual(
            ["scene_01", "scene_02"],
            [item["scene_id"] for item in statuses],
        )

    def test_index_upserts_preserve_sequential_and_concurrent_scenes(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        manager.submit(self._task_payload("scene_01"))
        manager.submit(self._task_payload("scene_02"))

        threads = [
            threading.Thread(
                target=manager._upsert_task_index,
                args=(
                    self.workflow_id,
                    self.run_id,
                    f"scene_{index:02d}",
                    manager.task_id_for(
                        self.workflow_id, self.run_id, f"scene_{index:02d}"
                    ),
                ),
            )
            for index in (3, 4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        index = json.loads(
            manager._task_index_path(self.workflow_id).read_text(encoding="utf-8")
        )
        self.assertEqual(
            {"scene_01", "scene_02", "scene_03", "scene_04"},
            set(index["runs"][self.run_id]),
        )

    def test_duplicate_queued_submit_does_not_enqueue_twice(self):
        manager = ImageRefreshTaskManager(self.assets_dir, self.coordinator)
        first, _ = manager.submit(self._task_payload("scene_01"))
        second, _ = manager.submit(self._task_payload("scene_01"))

        self.assertEqual(first["task_id"], second["task_id"])
        self.assertEqual(1, manager.queue.qsize())


if __name__ == "__main__":
    unittest.main()
