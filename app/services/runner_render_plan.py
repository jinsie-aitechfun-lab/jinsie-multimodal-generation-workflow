from __future__ import annotations

from typing import Any, Dict, List

from app.services.runner_errors import UnknownVideoProviderError


class RunnerRenderPlanSupport:
    """Builders for the per-provider render plan and final render package.

    Extracted from WorkflowRunner as Step 3 of the runner refactor.
    All methods are pure data assembly on dict payloads. Provider
    dispatch lives in build_render_plan_by_provider; provider-specific
    builders return a render-plan dict shape that the runner persists
    on outputs["render_plan"]. build_render_package assembles every
    artifact from the run into a single delivery payload.

    The class also owns the static Kling real-samples manifest factory
    (build_real_samples_manifest), which feeds both the render package
    and the public /v1/samples/* endpoints via thin wrappers on the
    runner.

    Behavior must remain byte-for-byte identical to the original
    methods in runner.py. The single external dependency
    (_normalized_video_provider on WorkflowRunner) is reached via
    self._runner, mirroring the pattern in RunnerImageReviewSupport.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def build_render_plan_by_provider(
        self, ctx: Any, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        provider = self._runner._normalized_video_provider(ctx.input.video_provider)

        if provider == "mock":
            return self.build_mock_render_plan(ctx, scenes, subtitles_enabled)
        if provider == "kling":
            return self.build_kling_render_plan(ctx, scenes, subtitles_enabled)
        if provider == "jimeng":
            return self.build_jimeng_render_plan(ctx, scenes, subtitles_enabled)

        raise UnknownVideoProviderError(f"Unknown video provider: {provider}")

    def base_asset_plan(
        self, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> List[Dict[str, Any]]:
        asset_plan: List[Dict[str, Any]] = []
        for scene in scenes:
            asset_plan.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "image_required": True,
                    "video_required": True,
                    "audio_required": True,
                    "subtitle_required": subtitles_enabled,
                }
            )
        return asset_plan

    def build_mock_render_plan(
        self, ctx: Any, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "output_mode": ctx.input.output_mode,
            "total_duration_sec": ctx.input.duration_sec,
            "scene_count": len(scenes),
            "asset_plan": self.base_asset_plan(scenes, subtitles_enabled),
            "edit_plan": {
                "subtitle_enabled": ctx.input.subtitle_enabled,
                "voice_style": ctx.input.voice_style,
                "visual_style": ctx.input.visual_style,
                "note": (
                    "Phase 1 render plan placeholder: "
                    "可继续对接可灵/即梦/剪映素材整合链路"
                ),
            },
        }

    def build_kling_render_plan(
        self, ctx: Any, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        return {
            "provider": "kling",
            "output_mode": ctx.input.output_mode,
            "total_duration_sec": ctx.input.duration_sec,
            "scene_count": len(scenes),
            "asset_plan": self.base_asset_plan(scenes, subtitles_enabled),
            "edit_plan": {
                "subtitle_enabled": ctx.input.subtitle_enabled,
                "voice_style": ctx.input.voice_style,
                "visual_style": ctx.input.visual_style,
                "adapter_status": "pending_api_integration",
                "next_step": "connect kling video generation api",
            },
        }

    def build_jimeng_render_plan(
        self, ctx: Any, scenes: List[Dict[str, Any]], subtitles_enabled: bool
    ) -> Dict[str, Any]:
        return {
            "provider": "jimeng",
            "output_mode": ctx.input.output_mode,
            "total_duration_sec": ctx.input.duration_sec,
            "scene_count": len(scenes),
            "asset_plan": self.base_asset_plan(scenes, subtitles_enabled),
            "edit_plan": {
                "subtitle_enabled": ctx.input.subtitle_enabled,
                "voice_style": ctx.input.voice_style,
                "visual_style": ctx.input.visual_style,
                "adapter_status": "pending_api_integration",
                "next_step": "connect jimeng video generation api",
            },
        }

    def build_real_samples_manifest(self) -> Dict[str, Any]:
        return {
            "provider": "kling",
            "manifest_type": "real_samples",
            "version": "v1",
            "samples": [
                {
                    "sample_id": "kling-scene-01-real-sample",
                    "scene_id": "scene-01",
                    "generated_scene_id": "scene_01",
                    "status": "archived",
                    "notes": (
                        "First real Kling scene sample archived for project "
                        "render-package backfill."
                    ),
                    "assets": {
                        "notes": "assets/samples/kling/scene-01/docs/scene-01-kling-notes.md",
                        "clean_video": "assets/samples/kling/scene-01/scene-01-kling-clean.mp4",
                        "watermarked_video": (
                            "assets/samples/kling/scene-01/scene-01-kling-watermarked.mp4"
                        ),
                        "input_screenshot": (
                            "assets/samples/kling/scene-01/screenshots/"
                            "scene-01-kling-input.png"
                        ),
                        "result_screenshots": [
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-01.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-02.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-03.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-04.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-05.png",
                            "assets/samples/kling/scene-01/screenshots/scene-01-kling-result-06.png",
                        ],
                    },
                }
            ],
        }

    def build_kling_scene_package(
        self, ctx: Any, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []
        if not scenes:
            return {}

        scene = scenes[0]
        visual_description = str(scene.get("visual_description", ""))
        narration = str(scene.get("narration", ""))
        shot_type = str(scene.get("shot_type", "wide"))
        transition = str(scene.get("transition", "fade"))
        duration_sec = int(scene.get("duration_sec", 15))

        recommended_prompt = (
            f"{ctx.input.visual_style} style video, {ctx.input.tone} atmosphere, "
            f"{ctx.input.character_style} protagonist, {visual_description}, "
            f"camera shot: {shot_type}, transition feeling: {transition}, "
            f"story context: {narration}"
        )

        return {
            "provider": "kling",
            "scene_id": scene.get("scene_id"),
            "scene_title": scene.get("scene_title"),
            "narration": narration,
            "visual_description": visual_description,
            "recommended_prompt": recommended_prompt,
            "recommended_duration_sec": duration_sec,
            "recommended_aspect_ratio": "9:16",
            "recommended_style": ctx.input.visual_style,
            "recommended_negative_prompt": (
                "low quality, blurry, distorted anatomy, broken composition, "
                "extra limbs, duplicated subject, unreadable details"
            ),
            "manual_generation_notes": [
                "打开可灵网页视频生成入口",
                "使用 recommended_prompt 作为主提示词",
                "时长优先使用 recommended_duration_sec",
                "画幅优先选择 9:16，适合短视频发布",
                "生成后将视频片段回填到项目四样例链中",
            ],
            "real_sample_manifest_ref": {
                "path": "assets/samples/kling/real_samples_manifest.json",
                "provider": "kling",
                "sample_id": "kling-scene-01-real-sample",
                "scene_id": "scene-01",
                "generated_scene_id": "scene_01",
            },
        }

    def build_render_package(
        self, ctx: Any, outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        story = outputs.get("story") or {}
        storyboard = outputs.get("storyboard") or {}
        image_prompts = outputs.get("image_prompts") or {}
        image_assets = outputs.get("image_assets") or {}
        video_prompts = outputs.get("video_prompts") or {}
        dialogue_script = outputs.get("dialogue_script") or {}
        audio_segments = outputs.get("audio_segments") or {}
        narration = outputs.get("narration") or {}
        subtitles = outputs.get("subtitles") or {}
        render_plan = outputs.get("render_plan") or {}
        final_video = outputs.get("final_video") or {}

        real_samples_manifest = self.build_real_samples_manifest()

        publish_manifest = {
            "topic": ctx.input.topic,
            "session_id": ctx.session_id,
            "video_provider": self._runner._normalized_video_provider(
                ctx.input.video_provider
            ),
            "output_mode": ctx.input.output_mode,
            "language": ctx.input.language,
            "voice_style": ctx.input.voice_style,
            "subtitle_enabled": ctx.input.subtitle_enabled,
            "scene_count": storyboard.get("scene_count"),
            "story_title": story.get("title"),
            "real_sample_manifest_ref": {
                "path": "assets/samples/kling/real_samples_manifest.json",
                "provider": "kling",
                "sample_count": len(real_samples_manifest.get("samples") or []),
            },
        }

        kling_scene_package = self.build_kling_scene_package(ctx, outputs)
        audio_assets_manifest = audio_segments.get("asset_manifest") or {
            "run_id": ctx.run_id,
            "provider": "mock_tts",
            "asset_count": 0,
            "assets": [],
        }
        audio_directory_manifest = audio_segments.get("directory_manifest") or {
            "run_directory": f"assets/mock/audio/{ctx.run_id}",
            "public_base_url": f"/assets/mock/audio/{ctx.run_id}",
            "index_file": "index.json",
            "index_public_url": f"/assets/mock/audio/{ctx.run_id}/index.json",
            "asset_files": [],
        }

        return {
            "format": "render_package_v1",
            "package_name": f"{ctx.workflow_id}_{ctx.run_id}",
            "files": {
                "story.json": story,
                "storyboard.json": storyboard,
                "image_prompts.json": image_prompts,
                "image_assets.json": image_assets,
                "video_prompts.json": video_prompts,
                "dialogue_script.json": dialogue_script,
                "audio_segments.json": audio_segments,
                "audio_directory_manifest.json": audio_directory_manifest,
                "audio_assets_manifest.json": audio_assets_manifest,
                "narration.txt": narration.get("full_text", ""),
                "subtitles.srt": subtitles.get("srt_preview", ""),
                "render_plan.json": render_plan,
                "final_video.json": final_video,
                "publish_manifest.json": publish_manifest,
                "kling_scene_package.json": kling_scene_package,
                "real_samples_manifest.json": real_samples_manifest,
            },
        }
