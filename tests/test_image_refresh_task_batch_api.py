from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main as main_module


class _EmptyBatchTaskManager:
    def list_for_run(self, workflow_id: str, run_id: str):
        return []


class ImageRefreshTaskBatchApiTests(unittest.TestCase):
    def test_missing_tasks_return_success_shape_with_found_false(self):
        original = main_module._image_refresh_tasks
        main_module._image_refresh_tasks = _EmptyBatchTaskManager()
        try:
            test_app = FastAPI()
            test_app.get("/v1/image-review/refresh-scene-tasks")(
                main_module.list_image_review_scene_tasks
            )
            response = TestClient(test_app).get(
                "/v1/image-review/refresh-scene-tasks",
                params={"workflow_id": "workflow_test", "run_id": "run_test"},
            )
        finally:
            main_module._image_refresh_tasks = original

        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json()["found"])
        self.assertEqual([], response.json()["tasks"])


if __name__ == "__main__":
    unittest.main()
