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

    def test_image_cards_prefer_thumbnails_and_original_action_keeps_public_url(self):
        review = (ROOT / "frontend/src/components/InteractiveImageReview.vue").read_text(
            encoding="utf-8"
        )
        card_path = review.split("function cardAssetPath", 1)[1].split(
            "function cardAssetVersion", 1
        )[0]
        original_path = review.split("function assetRefPath", 1)[1].split(
            "function cardAssetPath", 1
        )[0]
        self.assertLess(card_path.index("assetRef.thumbnail_url"), card_path.index("assetRef.public_url"))
        self.assertIn("assetRef.public_url || assetRef.relative_path", original_path)
        self.assertIn("function originalAssetHref", review)
        self.assertIn("thumbnail_version", review)

    def test_image_cards_use_bounded_real_reload_state_machine(self):
        review = (ROOT / "frontend/src/components/InteractiveImageReview.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("const IMAGE_RETRY_DELAYS_MS = [500, 1000, 2000] as const", review)
        self.assertIn("const imageRetryTimers = new Map<string, number>()", review)
        self.assertIn("imageRetryTimers.has(key)", review)
        self.assertIn("[key]: (imageRetryVersions.value[key] || 0) + 1", review)
        self.assertIn("setImageLoadState(key, 'failed')", review)
        self.assertIn("图片暂时加载失败", review)
        self.assertIn("重新加载", review)
        self.assertIn("查看原图", review)
        self.assertIn("onBeforeUnmount(() => {", review)
        self.assertIn("for (const timer of imageRetryTimers.values()) window.clearTimeout(timer)", review)
        self.assertNotIn("Date.now()", review)

    def test_image_asset_change_clears_old_retry_and_error_state(self):
        review = (ROOT / "frontend/src/components/InteractiveImageReview.vue").read_text(
            encoding="utf-8"
        )
        signature_watch = review.split("watch(assetVersionSignature", 1)[1].split(
            "onBeforeUnmount", 1
        )[0]
        self.assertIn("imageRetryTimers.clear()", signature_watch)
        self.assertIn("imageRetryAttempts.value = {}", signature_watch)
        self.assertIn("imageLoadStates.value = {}", signature_watch)
        self.assertIn("thumbnail_version", review)

    def test_image_loading_hints_prioritize_only_current_selected_image(self):
        review = (ROOT / "frontend/src/components/InteractiveImageReview.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn('loading="eager"', review)
        self.assertIn('fetchpriority="high"', review)
        self.assertIn('loading="lazy"', review)
        self.assertIn('fetchpriority="low"', review)
        self.assertGreaterEqual(review.count('decoding="async"'), 2)
        self.assertIn(':width="entry.item.selected_asset_ref?.thumbnail_width || 480"', review)
        self.assertIn(':height="entry.item.selected_asset_ref?.thumbnail_height || 270"', review)

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

    def test_queued_image_progress_waits_without_indeterminate_animation(self):
        source = (ROOT / "frontend/src/lib/workflowState.ts").read_text(encoding="utf-8")
        self.assertIn("任务已提交，等待开始 · ${completedLabel}", source)
        self.assertIn("const indeterminate = input.images.readyCount === 0 && hasRunning", source)

    def test_running_image_progress_shows_scene_and_real_completed_count(self):
        source = (ROOT / "frontend/src/lib/workflowState.ts").read_text(encoding="utf-8")
        self.assertIn("正在生成场景 ${Math.min(", source)
        self.assertIn("const completedLabel = `已完成 ${input.images.readyCount} / ${input.images.totalCount}`", source)
        self.assertIn("const percent = indeterminate\n      ? null", source)

    def test_partial_ready_progress_uses_ready_ratio(self):
        source = (ROOT / "frontend/src/lib/workflowState.ts").read_text(encoding="utf-8")
        image_branch = source.split(
            "if (input.images.totalCount > 0 && input.images.overallState !== 'idle')", 1
        )[1].split("return {\n    overallPercent: input.workflowPercent", 1)[0]
        self.assertIn("input.images.readyCount / input.images.totalCount", image_branch)
        self.assertIn("* 100", image_branch)
        self.assertNotIn("* 85", image_branch)
        self.assertIn("Math.round(", image_branch)
        self.assertEqual(17, round((1 / 6) * 100))

    def test_confirming_image_progress_has_confirmation_copy(self):
        source = (ROOT / "frontend/src/lib/workflowState.ts").read_text(encoding="utf-8")
        self.assertIn("正在确认生成结果 · ${completedLabel}", source)

    def test_completed_image_progress_is_100_percent(self):
        source = (ROOT / "frontend/src/lib/workflowState.ts").read_text(encoding="utf-8")
        self.assertIn("候选图生成完成 · ${completedLabel}", source)
        self.assertIn("(input.images.readyCount / input.images.totalCount) * 100", source)

    def test_video_url_starts_loading_instead_of_ready(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        video_state = source.split("type VideoPreviewLoadState", 1)[1].split(
            "const finalVideoAudioEnabled", 1
        )[0]
        self.assertIn("videoPreviewLoadState.value = url ? 'loading' : 'idle'", video_state)
        self.assertNotIn("videoPreviewLoadState.value = url ? 'ready'", video_state)
        self.assertIn("视频已生成，正在加载预览…", video_state)

    def test_loadedmetadata_marks_both_current_video_players_ready(self):
        preview = (ROOT / "frontend/src/components/studio/StudioPreviewPanel.vue").read_text(
            encoding="utf-8"
        )
        final_panel = (ROOT / "frontend/src/components/FinalVideoPanel.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn('@loadedmetadata="handleCurrentVideoReady"', preview)
        self.assertIn("if (isCurrentVideo.value) emit('video-ready')", preview)
        self.assertIn('@loadedmetadata="$emit(\'video-ready\')"', final_panel)

    def test_canplay_marks_both_current_video_players_ready(self):
        preview = (ROOT / "frontend/src/components/studio/StudioPreviewPanel.vue").read_text(
            encoding="utf-8"
        )
        final_panel = (ROOT / "frontend/src/components/FinalVideoPanel.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn('@canplay="handleCurrentVideoReady"', preview)
        self.assertIn('@canplay="$emit(\'video-ready\')"', final_panel)
        self.assertIn("videoPreviewLoadState.value = 'ready'", (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8"))

    def test_first_video_error_schedules_one_retry(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        video_state = source.split("type VideoPreviewLoadState", 1)[1].split(
            "const finalVideoAudioEnabled", 1
        )[0]
        self.assertIn("videoPreviewRetryTimer != null", video_state)
        self.assertIn("videoPreviewRetryCount.value += 1", video_state)
        self.assertIn("videoPreviewRetryTimer = window.setTimeout", video_state)

    def test_video_auto_retry_is_limited_to_two_attempts(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        self.assertIn("const VIDEO_PREVIEW_RETRY_DELAYS_MS = [1000, 2500] as const", source)
        self.assertIn("videoPreviewRetryCount.value >= VIDEO_PREVIEW_RETRY_DELAYS_MS.length", source)

    def test_video_retry_never_calls_final_video_render(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        video_state = source.split("type VideoPreviewLoadState", 1)[1].split(
            "const finalVideoAudioEnabled", 1
        )[0]
        self.assertNotIn("final-video/render", video_state)
        self.assertNotIn("fetch(", video_state)

    def test_video_retry_limit_enters_failed_state_with_recovery_actions(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        preview = (ROOT / "frontend/src/components/studio/StudioPreviewPanel.vue").read_text(
            encoding="utf-8"
        )
        final_panel = (ROOT / "frontend/src/components/FinalVideoPanel.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("videoPreviewLoadState.value = 'failed'", source)
        for component in (preview, final_panel):
            self.assertIn("视频预览加载失败", component + source)
            self.assertIn("重新加载", component)
            self.assertIn("打开原视频", component)

    def test_manual_video_reload_reenters_loading_with_existing_mp4(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        reload_body = source.split("function reloadVideoPreviewManually", 1)[1].split(
            "onBeforeUnmount(clearVideoPreviewRetryTimer)", 1
        )[0]
        self.assertIn("videoPreviewRetryVersion.value += 1", reload_body)
        self.assertIn("videoPreviewLoadState.value = 'loading'", reload_body)
        self.assertNotIn("Date.now", reload_body)

    def test_video_url_change_clears_old_failure_and_retry_state(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        url_watch = source.split("watch(finalVideoUrl", 1)[1].split(
            "function markVideoPreviewReady", 1
        )[0]
        self.assertIn("clearVideoPreviewRetryTimer()", url_watch)
        self.assertIn("videoPreviewRetryCount.value = 0", url_watch)
        self.assertIn("videoPreviewRetryVersion.value = 0", url_watch)
        self.assertIn("videoPreviewLoadState.value = url ? 'loading' : 'idle'", url_watch)

    def test_video_retry_timer_is_cleared_on_unmount(self):
        source = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        self.assertIn("onBeforeUnmount(clearVideoPreviewRetryTimer)", source)
        self.assertIn("window.clearTimeout(videoPreviewRetryTimer)", source)

    def test_current_video_panels_share_one_loading_state_semantics(self):
        preview = (ROOT / "frontend/src/components/studio/StudioPreviewPanel.vue").read_text(
            encoding="utf-8"
        )
        final_panel = (ROOT / "frontend/src/components/FinalVideoPanel.vue").read_text(
            encoding="utf-8"
        )
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        for component in (preview, final_panel):
            self.assertIn("videoLoadState", component)
            self.assertIn("videoStatusText", component)
            self.assertIn("video-ready", component)
            self.assertIn("video-error", component)
        self.assertIn(':video-load-state="videoPreviewLoadState"', studio)

    def test_history_video_metadata_persists_first_selected_asset_as_poster(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        derive_meta = studio.split("function deriveVideoMeta", 1)[1].split(
            "History video delete", 1
        )[0]
        self.assertIn("imageReview?.selected_assets", derive_meta)
        self.assertIn("selected_asset_ref", derive_meta)
        self.assertIn("posterUrl: posterUrl || undefined", derive_meta)
        self.assertIn("workflowId: response.workflow_id", derive_meta)
        self.assertIn("runId: response.run_id", derive_meta)
        self.assertIn("STORAGE_KEY_RECENT_VIDEO_META", studio)

    def test_history_poster_prefers_selected_asset_thumbnail(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        derive_meta = studio.split("function deriveVideoMeta", 1)[1].split(
            "History video delete", 1
        )[0]
        self.assertLess(derive_meta.index("thumbnail_url"), derive_meta.index(".public_url"))
        self.assertIn(".thumbnail_version", derive_meta)

    def test_async_history_poster_backfill_replaces_and_persists_fallback(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        push_recent = studio.split("function pushRecentFinalVideoUrl", 1)[1].split(
            "function deriveVideoMeta", 1
        )[0]
        self.assertIn("posterUrl: meta.posterUrl || existing.posterUrl", push_recent)
        self.assertNotIn("posterUrl: existing.posterUrl || meta.posterUrl", push_recent)
        self.assertIn(
            "localStorage.setItem(\n      STORAGE_KEY_RECENT_VIDEO_META",
            push_recent,
        )

    def test_history_cards_do_not_load_full_mp4_for_covers(self):
        preview = (ROOT / "frontend/src/components/studio/StudioPreviewPanel.vue").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('<video class="pp-thumb-video"', preview)
        self.assertNotIn('<video class="pp-hist-card-video"', preview)
        self.assertEqual(1, preview.count('<video\n            :src="currentPlayerUrl"'))

    def test_history_cards_use_poster_images_with_consistent_fallback(self):
        preview = (ROOT / "frontend/src/components/studio/StudioPreviewPanel.vue").read_text(
            encoding="utf-8"
        )
        self.assertEqual(3, preview.count('v-if="historyPosterUrl(url)"'))
        self.assertEqual(3, preview.count('loading="lazy"'))
        self.assertEqual(3, preview.count('aria-label="视频封面暂不可用"'))
        self.assertIn("markHistoryPosterFailed(url)", preview)
        self.assertIn(".pp-poster-placeholder", preview)

    def test_clicking_history_card_only_selects_existing_video_url(self):
        preview = (ROOT / "frontend/src/components/studio/StudioPreviewPanel.vue").read_text(
            encoding="utf-8"
        )
        select_body = preview.split("function selectVideo", 1)[1].split(
            "function shortUrl", 1
        )[0]
        self.assertIn("selectedUrl.value = url", select_body)
        self.assertNotIn("fetch(", select_body)
        self.assertNotIn("final-video/render", select_body)

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
        self.assertEqual(2, polling_body.count("fetchAuthoritativeWorkflow(workflowId, signal)"))
        terminal_block = polling_body.split("if (!hasActiveTask)", 1)[1]
        self.assertLess(terminal_block.index("return failures"), terminal_block.index("visibilityDelay"))
        self.assertIn("imageReviewRefreshAbortController?.abort()", unmount_body)
        self.assertIn("imageReviewPollingGeneration += 1", unmount_body)

    def test_manual_scene_regeneration_posts_a_fresh_task(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        refresh = studio.split("async function refreshImageReviewScene", 1)[1].split(
            "async function retryImageReviewScene", 1
        )[0]
        force_create = refresh.split("while (!task)", 1)[0]
        self.assertIn("if (retryFailed && allowCreate)", force_create)
        self.assertIn("retry_failed: true", force_create)
        self.assertIn("method: 'POST'", force_create)

    def test_succeeded_scenes_sync_incrementally_before_all_tasks_finish(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]
        incremental_sync = polling_body.split(
            "if (\n      hasActiveTask &&", 1
        )[1].split("if (!hasActiveTask)", 1)[0]

        self.assertIn("newlySucceededSceneIds.push(sceneId)", polling_body)
        self.assertIn("scenesNeedingResultSync.push(sceneId)", polling_body)
        self.assertIn("fetchAuthoritativeWorkflow(workflowId, signal)", incremental_sync)
        self.assertIn("applyWorkflowResponse(authoritative)", incremental_sync)
        self.assertIn("markPlaceholderState(sceneId, 'done')", incremental_sync)

    def test_first_and_second_succeeded_scenes_advance_ready_count(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        summary = studio.split(
            "const imageGenerationSummary", 1
        )[1].split("const isWorkflowReadyForRender", 1)[0]
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]

        self.assertIn("item.state === 'done'\n          ? 'ready'", summary)
        self.assertIn("syncedSucceededSceneIds.add(sceneId)", polling_body)
        self.assertIn("markPlaceholderState(sceneId, 'done')", polling_body)

    def test_succeeded_scene_is_not_synchronized_twice_after_success(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]

        self.assertIn("const syncedSucceededSceneIds = new Set<string>()", polling_body)
        self.assertIn("if (syncedSucceededSceneIds.has(sceneId))", polling_body)
        self.assertIn("!syncedSucceededSceneIds.has(sceneId)", polling_body)

    def test_failed_result_sync_stays_confirming_without_reposting(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]
        create_guard = polling_body.split("const shouldCreateMissing", 1)[1].split(")\n      if", 1)[0]
        incremental_sync = polling_body.split(
            "if (\n      hasActiveTask &&", 1
        )[1].split("if (!hasActiveTask)", 1)[0]

        self.assertIn("!observedSucceededSceneIds.has(sceneId)", create_guard)
        self.assertIn("catch (error)", incremental_sync)
        self.assertIn("markPlaceholderState(sceneId, 'confirming')", incremental_sync)
        self.assertNotIn("createImageRefreshTask(", incremental_sync)

    def test_all_terminal_still_performs_final_authoritative_reconciliation(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]
        terminal_block = polling_body.split("if (!hasActiveTask)", 1)[1]

        self.assertIn("final authoritative reconciliation", terminal_block)
        self.assertIn("fetchAuthoritativeWorkflow(workflowId, signal)", terminal_block)
        self.assertIn("applyWorkflowResponse(authoritative)", terminal_block)

    def test_missing_batch_tasks_are_submitted_once_per_workflow(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        polling_body = studio.split(
            "async function pollImageRefreshTasksForWorkflow", 1
        )[1].split("async function refreshImageReview", 1)[0]

        self.assertIn("submittedImageTaskSceneIdsByWorkflow", studio)
        self.assertIn("submittedSceneIds.has(sceneId)", polling_body)
        self.assertIn("submittedSceneIds.add(sceneId)", polling_body)
        self.assertIn("!submittedSceneIds.has(sceneId)", polling_body)
        self.assertIn("markPlaceholderState(sceneId, 'confirming')", polling_body)
        self.assertIn("submittedImageTaskSceneIdsByWorkflow.get(workflowKey)", polling_body)

    def test_workflow_identity_is_persisted_before_create_request(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        execute = studio.split("async function executeRunWorkflow", 1)[1].split(
            "</script>", 1
        )[0]
        self.assertIn("const STORAGE_KEY_RUN = 'jinsie_run_id'", studio)
        self.assertLess(
            execute.index("persistActiveWorkflowIdentity(workflowId)"),
            execute.index("/v1/workflow/run"),
        )
        self.assertIn("persistActiveWorkflowIdentity(workflowId, data.run_id || '')", studio)

    def test_studio_reentry_uses_one_authoritative_restore_entry(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        restore = studio.split("async function restorePersistedWorkflowState", 1)[1].split(
            "function onStudioPageShow", 1
        )[0]
        self.assertIn("if (workflowRestorePromise) return workflowRestorePromise", restore)
        self.assertIn("/v1/workflow/results/", restore)
        self.assertIn("applyWorkflowResponse(data)", restore)
        self.assertIn("resumePendingSceneGenerationAfterRestore()", restore)
        self.assertIn("void restorePersistedWorkflowState('mount')", studio)
        self.assertIn("void restorePersistedWorkflowState('pageshow')", studio)
        self.assertIn("void restorePersistedWorkflowState('visibility')", studio)

    def test_reentry_resumes_image_polling_without_creating_tasks(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        resume = studio.split("function resumePendingSceneGenerationAfterRestore", 1)[1].split(
            "async function waitForAsyncWorkflowOutputs", 1
        )[0]
        self.assertIn("void refreshImageReview(false)", resume)
        self.assertNotIn("refresh-scene-tasks", resume)
        self.assertNotIn("method: 'POST'", resume)

    def test_final_video_render_marker_prevents_duplicate_post(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        render = studio.split("async function renderFinalVideoIfReady", 1)[1].split(
            "function waitForTaskPoll", 1
        )[0]
        self.assertLess(
            render.index("readFinalVideoRenderMarker(renderWorkflowId)"),
            render.index("fetch(`${apiBaseUrl}/v1/final-video/render`"),
        )
        self.assertLess(
            render.index("persistFinalVideoRenderMarker(renderWorkflowId"),
            render.index("fetch(`${apiBaseUrl}/v1/final-video/render`"),
        )
        self.assertIn("scheduleFinalVideoAuthoritativeRecovery(renderWorkflowId)", render)

    def test_final_video_recovery_only_reads_authoritative_results(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        recovery = studio.split("function scheduleFinalVideoAuthoritativeRecovery", 1)[1].split(
            "function isDeletedWorkflowResponse", 1
        )[0]
        self.assertIn("fetchAuthoritativeWorkflow(workflowId)", recovery)
        self.assertIn("applyWorkflowResponse(data)", recovery)
        self.assertNotIn("final-video/render", recovery)
        self.assertNotIn("method: 'POST'", recovery)

    def test_completed_video_clears_render_recovery_state(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        apply_response = studio.split("function applyWorkflowResponse", 1)[1].split(
            "function buildReviewPlaceholdersFromStoryboard", 1
        )[0]
        self.assertIn("clearFinalVideoRenderMarker", apply_response)
        self.assertIn("clearFinalVideoRecoveryTimer()", apply_response)
        self.assertIn("finalVideoRenderInFlight.value = false", apply_response)

    def test_resume_listeners_and_video_timer_are_cleaned_on_unmount(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        unmount = studio.split("onBeforeUnmount(() => {", 1)[1].split("})", 1)[0]
        self.assertIn("removeEventListener('pageshow', onStudioPageShow)", unmount)
        self.assertIn("removeEventListener('visibilitychange', onImageReviewVisibilityChange)", unmount)
        self.assertIn("clearFinalVideoRecoveryTimer()", unmount)

    def test_new_workflow_invalidates_old_lifecycle_recovery(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        execute = studio.split("async function executeRunWorkflow", 1)[1].split(
            "</script>", 1
        )[0]
        self.assertIn("let workflowLifecycleGeneration = 0", studio)
        self.assertIn("workflowLifecycleGeneration += 1", studio)
        self.assertLess(
            execute.index("invalidateWorkflowLifecycleRecovery()"),
            execute.index("persistActiveWorkflowIdentity(workflowId)"),
        )
        self.assertIn("clearFinalVideoRecoveryTimer()", studio)

    def test_restore_rejects_old_workflow_response_before_apply(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        restore = studio.split("async function restorePersistedWorkflowState", 1)[1].split(
            "function onStudioPageShow", 1
        )[0]
        direct_result = restore.split(
            "const data = (await resultsResponse.json()) as WorkflowRunResponse", 1
        )[1].split("if (resultsResponse.status !== 404)", 1)[0]
        self.assertLess(
            direct_result.index("isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)"),
            direct_result.index("applyWorkflowResponse(data)"),
        )
        self.assertIn("isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)", restore)
        self.assertIn("workflowRestorePromise === restorePromise", restore)

    def test_final_video_poll_rejects_old_marker_before_apply(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        recovery = studio.split("function scheduleFinalVideoAuthoritativeRecovery", 1)[1].split(
            "function isDeletedWorkflowResponse", 1
        )[0]
        after_fetch = recovery.split("const data = await fetchAuthoritativeWorkflow(workflowId)", 1)[1]
        before_apply = after_fetch.split("applyWorkflowResponse(data)", 1)[0]
        self.assertIn("isCurrentWorkflowLifecycle(workflowId, recoveryGeneration)", before_apply)
        self.assertIn("readFinalVideoRenderMarker(workflowId)", before_apply)
        self.assertIn("recoveryGeneration", recovery)

    def test_old_final_render_response_cannot_overwrite_new_workflow(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        render = studio.split("async function renderFinalVideoIfReady", 1)[1].split(
            "function waitForTaskPoll", 1
        )[0]
        response_block = render.split(
            "const data: FinalVideoRenderResponse = await response.json()", 1
        )[1].split("applyWorkflowResponse(mergedResponse)", 1)[0]
        self.assertIn("isCurrentWorkflowLifecycle(renderWorkflowId, renderGeneration)", response_block)
        self.assertIn("readFinalVideoRenderMarker(renderWorkflowId)", response_block)


    def test_studio_shell_flex_items_can_shrink_to_mobile_viewport(self):
        layout = (ROOT / "frontend/src/components/studio/StudioLayout.vue").read_text(
            encoding="utf-8"
        )
        content = layout.split(".s-content {", 1)[1].split("}", 1)[0]
        main = layout.split(".s-main {", 1)[1].split("}", 1)[0]
        root = layout.split(".s-root {", 1)[1].split("}", 1)[0]
        self.assertIn("min-width: 0", root)
        self.assertIn("max-width: 100%", root)
        self.assertIn("min-width: 0", content)
        self.assertIn("max-width: calc(100% - 88px)", content)
        self.assertIn("min-width: 0", main)
        self.assertNotIn("overflow-x: hidden", content)

    def test_studio_home_grid_tracks_and_children_have_zero_minimums(self):
        studio = (ROOT / "frontend/src/views/StudioView.vue").read_text(encoding="utf-8")
        grid = studio.split(".studio-home-grid {", 1)[1].split("}", 1)[0]
        children = studio.split(".studio-home-grid > * {", 1)[1].split("}", 1)[0]
        self.assertIn("grid-template-columns: minmax(0, 420px) minmax(0, 1fr)", grid)
        self.assertIn("max-width: 100%", grid)
        self.assertIn("min-width: 0", grid)
        self.assertIn("min-width: 0", children)
        self.assertIn("max-width: 100%", children)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", studio)

    def test_landing_hero_navigation_has_immediate_loading_feedback(self):
        landing = (ROOT / "frontend/src/components/landing/LandingPage.vue").read_text(
            encoding="utf-8"
        )
        hero_button = landing.split('<div class="hero-cta-row">', 1)[1].split(
            "</button>", 1
        )[0]
        navigation = landing.split("async function goStudioFromHero", 1)[1].split(
            "/* ── Showcase", 1
        )[0]
        self.assertIn(':disabled="heroNavigating"', hero_button)
        self.assertIn(':aria-busy="heroNavigating"', hero_button)
        self.assertIn('@click="goStudioFromHero"', hero_button)
        self.assertIn("正在进入工作台...", hero_button)
        self.assertIn("hero-primary-spinner", hero_button)
        self.assertIn("if (heroNavigating.value) return", navigation)
        self.assertLess(
            navigation.index("heroNavigating.value = true"),
            navigation.index("await goStudio()"),
        )
        self.assertIn("finally", navigation)
        self.assertIn("heroNavigating.value = false", navigation)

    def test_landing_loading_is_scoped_to_the_hero_button(self):
        landing = (ROOT / "frontend/src/components/landing/LandingPage.vue").read_text(
            encoding="utf-8"
        )
        self.assertEqual(1, landing.count('@click="goStudioFromHero"'))
        self.assertGreaterEqual(landing.count('@click="goStudio"'), 2)


if __name__ == "__main__":
    unittest.main()
