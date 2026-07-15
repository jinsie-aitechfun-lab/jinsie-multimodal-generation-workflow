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


if __name__ == "__main__":
    unittest.main()
