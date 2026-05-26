import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import requests


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


_WORKFLOW_STEPS = [
    {"name": "story"},
    {"name": "storyboard"},
    {"name": "image_prompts"},
    {"name": "video_prompts"},
    {"name": "dialogue_script"},
    {"name": "audio_segments"},
    {"name": "narration"},
    {"name": "subtitles"},
    {"name": "render_plan"},
]


def _submit_workflow(
    base_url: str,
    session_id: str,
    topic: str,
) -> str:
    """POST /v1/workflow/run, assert async acceptance, return workflow_id."""
    payload: Dict[str, Any] = {
        "workflow_id": "storybook-demo",
        "session_id": session_id,
        "input": {
            "topic": topic,
            "audience": "children",
            "tone": "warm",
            "visual_style": "storybook",
            "character_style": "animal",
            "voice_style": "warm_female",
            "voiceover_enabled": True,
            "voice_mode": "multi",
            "speaker_profiles": {
                "narrator": "warm_female",
                "mother": "warm_female",
                "child": "gentle_child",
            },
            "duration_sec": 60,
            "language": "zh-CN",
            "subtitle_enabled": True,
            "video_provider": "mock",
            "output_mode": "full_video",
        },
        "steps": _WORKFLOW_STEPS,
    }
    r = requests.post(f"{base_url}/v1/workflow/run", json=payload, timeout=15)
    if r.status_code != 200:
        _fail(f"/v1/workflow/run http_status={r.status_code}, body={r.text}")
    body = r.json()
    if body.get("status") != "processing":
        _fail(f"/v1/workflow/run status != processing: {body}")
    workflow_id = body.get("workflow_id")
    if not workflow_id:
        _fail(f"/v1/workflow/run missing workflow_id: {body}")
    return workflow_id


def _poll_until_complete(
    base_url: str,
    workflow_id: str,
    timeout_sec: int = 120,
    poll_interval_sec: float = 1.5,
) -> None:
    """Poll GET /v1/workflow/status until completed or timeout."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        r = requests.get(
            f"{base_url}/v1/workflow/status/{workflow_id}", timeout=5
        )
        if r.status_code != 200:
            _fail(
                f"/v1/workflow/status/{workflow_id} http_status={r.status_code}"
            )
        body = r.json()
        status = body.get("status")
        if status == "completed":
            return
        if status == "failed":
            _fail(f"workflow {workflow_id} failed: {body}")
        time.sleep(poll_interval_sec)
    _fail(f"workflow {workflow_id} did not complete within {timeout_sec}s")


def _load_outputs(workflow_id: str) -> Dict[str, Any]:
    """Read outputs.json written by the async runner."""
    outputs_path = Path("assets/mock") / workflow_id / "outputs.json"
    if not outputs_path.exists():
        _fail(f"outputs.json not found: {outputs_path}")
    with open(outputs_path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8004")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    session_id = f"acceptance-session-{uuid4().hex[:8]}"

    # 1) /health
    r = requests.get(f"{base_url}/health", timeout=5)
    if r.status_code != 200:
        _fail(f"/health http_status={r.status_code}")
    body = r.json()
    if body.get("status") != "ok":
        _fail(f"/health body.status != ok, body={body}")
    _ok("/health")

    # 2) /v1/samples/summary
    r = requests.get(f"{base_url}/v1/samples/summary", timeout=5)
    if r.status_code != 200:
        _fail(f"/v1/samples/summary http_status={r.status_code}, body={r.text}")
    summary_body = r.json()

    providers = summary_body.get("providers") or []
    if not isinstance(providers, list) or "kling" not in providers:
        _fail(f"/v1/samples/summary providers invalid: {summary_body}")

    if summary_body.get("total_sample_count") != 1:
        _fail(f"/v1/samples/summary total_sample_count mismatch: {summary_body}")

    provider_stats = summary_body.get("provider_stats") or {}
    kling_stats = provider_stats.get("kling") or {}
    if kling_stats.get("sample_count") != 1:
        _fail(f"/v1/samples/summary kling sample_count mismatch: {summary_body}")
    if kling_stats.get("latest_sample_id") != "kling-scene-01-real-sample":
        _fail(f"/v1/samples/summary kling latest_sample_id mismatch: {summary_body}")

    available_scene_ids = kling_stats.get("available_scene_ids") or []
    if not isinstance(available_scene_ids, list) or "scene-01" not in available_scene_ids:
        _fail(f"/v1/samples/summary kling available_scene_ids mismatch: {summary_body}")

    _ok("/v1/samples/summary")

    # 3) /v1/samples/kling/real
    r = requests.get(f"{base_url}/v1/samples/kling/real", timeout=5)
    if r.status_code != 200:
        _fail(f"/v1/samples/kling/real http_status={r.status_code}, body={r.text}")
    real_samples_body = r.json()

    if real_samples_body.get("provider") != "kling":
        _fail(f"/v1/samples/kling/real provider mismatch: {real_samples_body}")
    if real_samples_body.get("manifest_type") != "real_samples":
        _fail(f"/v1/samples/kling/real manifest_type mismatch: {real_samples_body}")

    api_samples = real_samples_body.get("samples") or []
    if not isinstance(api_samples, list) or len(api_samples) < 1:
        _fail(f"/v1/samples/kling/real samples invalid: {real_samples_body}")

    if real_samples_body.get("sample_count") != 1:
        _fail(f"/v1/samples/kling/real sample_count mismatch: {real_samples_body}")
    if real_samples_body.get("latest_sample_id") != "kling-scene-01-real-sample":
        _fail(f"/v1/samples/kling/real latest_sample_id mismatch: {real_samples_body}")

    api_available_scene_ids = real_samples_body.get("available_scene_ids") or []
    if not isinstance(api_available_scene_ids, list) or "scene-01" not in api_available_scene_ids:
        _fail(f"/v1/samples/kling/real available_scene_ids mismatch: {real_samples_body}")

    api_sample_1 = api_samples[0]
    if api_sample_1.get("sample_id") != "kling-scene-01-real-sample":
        _fail(f"/v1/samples/kling/real sample_id mismatch: {api_sample_1}")
    if api_sample_1.get("scene_id") != "scene-01":
        _fail(f"/v1/samples/kling/real scene_id mismatch: {api_sample_1}")

    api_assets = api_sample_1.get("assets") or {}
    if api_assets.get("clean_video") != (
        "assets/samples/kling/scene-01/scene-01-kling-clean.mp4"
    ):
        _fail(f"/v1/samples/kling/real clean_video mismatch: {api_assets}")
    api_result_screenshots = api_assets.get("result_screenshots") or []
    if not isinstance(api_result_screenshots, list) or len(api_result_screenshots) != 6:
        _fail(f"/v1/samples/kling/real result_screenshots invalid: {api_assets}")

    _ok("/v1/samples/kling/real")

    # 4) /v1/samples/kling/real/{sample_id}
    r = requests.get(
        f"{base_url}/v1/samples/kling/real/kling-scene-01-real-sample",
        timeout=5,
    )
    if r.status_code != 200:
        _fail(
            f"/v1/samples/kling/real/{{sample_id}} http_status={r.status_code}, "
            f"body={r.text}"
        )
    detail_body = r.json()

    if detail_body.get("sample_id") != "kling-scene-01-real-sample":
        _fail(f"/v1/samples/kling/real/{{sample_id}} sample_id mismatch: {detail_body}")
    if detail_body.get("scene_id") != "scene-01":
        _fail(f"/v1/samples/kling/real/{{sample_id}} scene_id mismatch: {detail_body}")

    detail_assets = detail_body.get("assets") or {}
    if detail_assets.get("clean_video") != (
        "assets/samples/kling/scene-01/scene-01-kling-clean.mp4"
    ):
        _fail(
            f"/v1/samples/kling/real/{{sample_id}} clean_video mismatch: "
            f"{detail_assets}"
        )

    r = requests.get(f"{base_url}/v1/samples/kling/real/not-exist", timeout=5)
    if r.status_code != 404:
        _fail(
            f"/v1/samples/kling/real/not-exist http_status={r.status_code}, "
            f"body={r.text}"
        )
    not_found_body = r.json()
    if not_found_body.get("detail") != "sample not found: not-exist":
        _fail(
            f"/v1/samples/kling/real/not-exist detail mismatch: "
            f"{not_found_body}"
        )

    _ok("/v1/samples/kling/real/{sample_id}")

    # 5) first run
    wf_id1 = _submit_workflow(base_url, session_id, "小兔子的一天")
    _poll_until_complete(base_url, wf_id1)
    resp1 = _load_outputs(wf_id1)
    _ok(f"/v1/workflow/run (async, {wf_id1})")

    if resp1.get("workflow_id") != "storybook-demo":
        _fail(f"workflow_id mismatch: {resp1.get('workflow_id')}")
    if resp1.get("session_id") != session_id:
        _fail(f"session_id mismatch: {resp1.get('session_id')}")
    if not str(resp1.get("run_id", "")).startswith("run_"):
        _fail(f"run_id invalid: {resp1.get('run_id')}")
    if resp1.get("status") != "COMPLETED":
        _fail(f"status != COMPLETED: {resp1.get('status')}")

    steps = resp1.get("steps")
    if not isinstance(steps, list) or len(steps) != 9:
        _fail(f"steps invalid len: {steps}")

    expected_names = [
        "story",
        "storyboard",
        "image_prompts",
        "video_prompts",
        "dialogue_script",
        "audio_segments",
        "narration",
        "subtitles",
        "render_plan",
    ]
    actual_names = [step.get("name") for step in steps]
    if actual_names != expected_names:
        _fail(f"step names mismatch: {actual_names}")

    outputs = resp1.get("outputs") or {}
    for key in expected_names:
        if key not in outputs:
            _fail(f"missing output key: {key}")

    memory1 = resp1.get("session_memory_summary") or {}
    if memory1.get("enabled") is not True:
        _fail(f"session_memory_summary.enabled invalid: {memory1}")
    if memory1.get("has_previous_session") is not False:
        _fail(f"first request should have no previous session: {memory1}")

    render_package1 = resp1.get("render_package") or {}
    files1 = render_package1.get("files") or {}
    expected_package_keys = [
        "story.json",
        "storyboard.json",
        "image_prompts.json",
        "video_prompts.json",
        "dialogue_script.json",
        "audio_segments.json",
        "narration.txt",
        "subtitles.srt",
        "render_plan.json",
        "publish_manifest.json",
        "kling_scene_package.json",
        "real_samples_manifest.json",
    ]
    for key in expected_package_keys:
        if key not in files1:
            _fail(f"missing render package file: {key}")

    if not files1.get("narration.txt"):
        _fail("render_package narration.txt empty")
    if not files1.get("subtitles.srt"):
        _fail("render_package subtitles.srt empty")

    kling_scene_package1 = files1.get("kling_scene_package.json") or {}
    if kling_scene_package1.get("provider") != "kling":
        _fail(f"kling_scene_package provider mismatch: {kling_scene_package1}")
    if kling_scene_package1.get("scene_id") != "scene_01":
        _fail(f"kling_scene_package scene_id mismatch: {kling_scene_package1}")
    if kling_scene_package1.get("recommended_aspect_ratio") != "9:16":
        _fail(f"kling_scene_package aspect ratio mismatch: {kling_scene_package1}")
    if not kling_scene_package1.get("recommended_prompt"):
        _fail("kling_scene_package recommended_prompt empty")

    real_manifest1 = files1.get("real_samples_manifest.json") or {}
    if real_manifest1.get("provider") != "kling":
        _fail(f"real_samples_manifest provider mismatch: {real_manifest1}")
    samples1 = real_manifest1.get("samples") or []
    if not isinstance(samples1, list) or len(samples1) != 1:
        _fail(f"real_samples_manifest samples invalid: {real_manifest1}")

    dialogue_script1 = files1.get("dialogue_script.json") or {}
    if dialogue_script1.get("enabled") is not True:
        _fail(f"dialogue_script enabled mismatch: {dialogue_script1}")
    if dialogue_script1.get("voice_mode") != "multi":
        _fail(f"dialogue_script voice_mode mismatch: {dialogue_script1}")

    lines1 = dialogue_script1.get("lines") or []
    if not isinstance(lines1, list) or len(lines1) == 0:
        _fail(f"dialogue_script lines invalid: {dialogue_script1}")

    speakers1 = {line.get("speaker") for line in lines1}
    if "mother" not in speakers1 or "child" not in speakers1:
        _fail(f"dialogue_script speakers invalid: {dialogue_script1}")

    narration1 = outputs.get("narration") or {}
    if narration1.get("voice_mode") != "multi":
        _fail(f"narration voice_mode mismatch: {narration1}")

    narration_segments1 = narration1.get("segments") or []
    if not isinstance(narration_segments1, list) or len(narration_segments1) == 0:
        _fail(f"narration segments invalid: {narration1}")

    narration_speakers1 = {segment.get("speaker") for segment in narration_segments1}
    if "mother" not in narration_speakers1 or "child" not in narration_speakers1:
        _fail(f"narration speakers invalid: {narration1}")
    
    audio_segments1 = files1.get("audio_segments.json") or {}
    if audio_segments1.get("enabled") is not True:
        _fail(f"audio_segments enabled mismatch: {audio_segments1}")

    audio_items1 = audio_segments1.get("items") or []
    if not isinstance(audio_items1, list) or len(audio_items1) == 0:
        _fail(f"audio_segments items invalid: {audio_segments1}")

    first_audio_item1 = audio_items1[0]
    if first_audio_item1.get("provider") != "mock_tts":
        _fail(f"audio_segments provider mismatch: {audio_segments1}")
    if first_audio_item1.get("status") != "planned":
        _fail(f"audio_segments status mismatch: {audio_segments1}")
    if not first_audio_item1.get("target_audio_file"):
        _fail(f"audio_segments target_audio_file empty: {audio_segments1}")
            
    sample1 = samples1[0]
    if sample1.get("scene_id") != "scene-01":
        _fail(f"real sample scene_id mismatch: {sample1}")
    if sample1.get("generated_scene_id") != "scene_01":
        _fail(f"real sample generated_scene_id mismatch: {sample1}")

    sample_assets1 = sample1.get("assets") or {}
    if sample_assets1.get("clean_video") != (
        "assets/samples/kling/scene-01/scene-01-kling-clean.mp4"
    ):
        _fail(f"real sample clean_video mismatch: {sample_assets1}")
    result_screenshots1 = sample_assets1.get("result_screenshots") or []
    if not isinstance(result_screenshots1, list) or len(result_screenshots1) != 6:
        _fail(f"real sample result_screenshots invalid: {sample_assets1}")

    publish_manifest1 = files1.get("publish_manifest.json") or {}
    real_manifest_ref1 = publish_manifest1.get("real_sample_manifest_ref") or {}
    if real_manifest_ref1.get("path") != "assets/samples/kling/real_samples_manifest.json":
        _fail(f"publish_manifest real_sample_manifest_ref mismatch: {publish_manifest1}")

    kling_real_ref1 = kling_scene_package1.get("real_sample_manifest_ref") or {}
    if kling_real_ref1.get("sample_id") != "kling-scene-01-real-sample":
        _fail(
            f"kling_scene_package real_sample_manifest_ref mismatch: "
            f"{kling_scene_package1}"
        )

    # 6) second run with same session id
    wf_id2 = _submit_workflow(base_url, session_id, "小兔子的新冒险")
    _poll_until_complete(base_url, wf_id2)
    resp2 = _load_outputs(wf_id2)
    _ok(f"/v1/workflow/run second run (async, {wf_id2})")
    memory2 = resp2.get("session_memory_summary") or {}

    if memory2.get("enabled") is not True:
        _fail(f"second session memory not enabled: {memory2}")
    if memory2.get("has_previous_session") is not True:
        _fail(f"second request should detect previous session: {memory2}")
    if memory2.get("previous_topic") != "小兔子的一天":
        _fail(f"previous_topic mismatch: {memory2}")
    if memory2.get("previous_scene_count") != 4:
        _fail(f"previous_scene_count mismatch: {memory2}")

    render_package2 = resp2.get("render_package") or {}
    files2 = render_package2.get("files") or {}
    manifest2 = files2.get("publish_manifest.json") or {}
    if manifest2.get("topic") != "小兔子的新冒险":
        _fail(f"publish_manifest topic mismatch: {manifest2}")
    if manifest2.get("video_provider") != "mock":
        _fail(f"publish_manifest video_provider mismatch: {manifest2}")

    kling_scene_package2 = files2.get("kling_scene_package.json") or {}
    if kling_scene_package2.get("scene_title") != "故事开场":
        _fail(f"kling_scene_package scene_title mismatch: {kling_scene_package2}")
    notes = kling_scene_package2.get("manual_generation_notes") or []
    if not isinstance(notes, list) or len(notes) == 0:
        _fail(f"kling_scene_package manual_generation_notes invalid: {kling_scene_package2}")

    _ok("all workflow assertions passed")
    print(json.dumps(resp2, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()