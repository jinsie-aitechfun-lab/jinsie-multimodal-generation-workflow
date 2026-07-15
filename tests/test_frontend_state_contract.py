from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class FrontendStateContractTests(unittest.TestCase):
    def test_task_polling_and_progress_have_no_old_render_constants(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        final_panel = (ROOT / "frontend/src/components/FinalVideoPanel.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("refresh-scene-task", studio)
        self.assertIn("'confirming'", studio)
        self.assertNotIn("finalVideoRenderInFlight\n              ? 92", studio)
        self.assertNotIn("return 90", final_panel)

    def test_route_restore_uses_recovery_mode(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        self.assertIn("void refreshImageReview(false)", studio)
        self.assertIn("if (!allowCreate)", studio)
        self.assertIn("['waiting', 'queued', 'refreshing', 'confirming']", studio)

    def test_stable_server_version_replaces_scene_date_now(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        self.assertIn("candidate_asset_refs", studio)
        self.assertNotIn("[sceneId]: Date.now()", studio)

    def test_image_get_retry_never_calls_generation_api(self):
        review = (ROOT / "frontend/src/components/InteractiveImageReview.vue").read_text(
            encoding="utf-8"
        )
        retry_body = review.split("function retryImageGet", 1)[1].split("\n}", 1)[0]
        self.assertIn("imageRetryAttempts", retry_body)
        self.assertNotIn("refresh-scene", retry_body)

    def test_top_and_final_panel_receive_the_same_summaries(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        final_panel = (ROOT / "frontend/src/components/FinalVideoPanel.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn(':workflow-progress-summary="workflowProgressSummary"', studio)
        self.assertIn(':image-generation-summary="imageGenerationSummary"', studio)
        self.assertIn("props.workflowProgressSummary", final_panel)
        self.assertIn("props.imageGenerationSummary", final_panel)

    def test_render_progress_is_indeterminate_and_completion_is_100(self):
        source = (ROOT / "frontend/src/lib/workflowState.ts").read_text(encoding="utf-8")
        render_branch = source.split("if (input.rendering)", 1)[1].split(
            "if (input.awaitingRender)", 1
        )[0]
        completed_branch = source.split("if (input.completed)", 1)[1].split(
            "if (input.rendering)", 1
        )[0]
        self.assertIn("overallPercent: null", render_branch)
        self.assertIn("indeterminate: true", render_branch)
        self.assertIn("overallPercent: 100", completed_branch)

    def test_image_refresh_uses_one_workflow_batch_polling_loop(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        refresh_body = studio.split("async function refreshImageReview", 1)[1].split(
            "function scheduleImageReviewAutoRefreshIfNeeded", 1
        )[0]
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]

        self.assertIn("/v1/image-review/refresh-scene-tasks?", studio)
        self.assertIn("pollImageRefreshTasksForWorkflow(", refresh_body)
        self.assertNotIn("Promise.all(", refresh_body)
        self.assertEqual(1, polling_body.count("fetchImageRefreshTaskBatch("))
        self.assertIn("await fetchImageRefreshTaskBatch", polling_body)
        self.assertIn("await waitForImageReviewBatchPoll", polling_body)
        self.assertNotIn("setInterval", polling_body)

    def test_image_refresh_polling_has_lifecycle_and_terminal_guards(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]
        unmount_body = studio.split("onBeforeUnmount(() => {", 1)[1].split("})", 1)[0]

        self.assertIn("activeImageReviewPollingKey !== workflowKey", polling_body)
        self.assertIn("generation !== imageReviewPollingGeneration", polling_body)
        self.assertIn("document.hidden ? 20000 : 5000", polling_body)
        self.assertIn("if (!hasActiveTask)", polling_body)
        self.assertEqual(1, polling_body.count("fetchAuthoritativeWorkflow(workflowId, signal)"))
        terminal_block = polling_body.split("if (!hasActiveTask)", 1)[1]
        self.assertLess(terminal_block.index("return failures"), terminal_block.index("visibilityDelay"))
        self.assertIn("imageReviewRefreshAbortController?.abort()", unmount_body)
        self.assertIn("imageReviewPollingGeneration += 1", unmount_body)


if __name__ == "__main__":
    unittest.main()
