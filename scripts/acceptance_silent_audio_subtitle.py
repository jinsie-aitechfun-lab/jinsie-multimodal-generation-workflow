#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
VIDEO_ROOT = REPO_ROOT / "assets" / "mock" / "video"


@dataclass
class CaseConfig:
    name: str
    audio_enabled: bool
    voiceover_enabled: bool
    subtitle_enabled: bool
    render_mode: str  # "auto" or "manual"


def _run(
    cmd: List[str], *, cwd: Optional[Path] = None, check: bool = True
) -> subprocess.CompletedProcess:
    p = subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True
    )
    if check and p.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  code: {p.returncode}\n"
            f"  stdout:\n{p.stdout}\n"
            f"  stderr:\n{p.stderr}\n"
        )
    return p


def _curl_json(
    api_base: str, path: str, payload: Dict[str, Any], timeout_sec: int = 180
) -> Dict[str, Any]:
    tmp = Path("/tmp/_acceptance_req.json")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd = [
        "curl",
        "-sS",
        "--max-time",
        str(timeout_sec),
        "-X",
        "POST",
        f"{api_base}{path}",
        "-H",
        "Content-Type: application/json",
        "--data",
        f"@{str(tmp)}",
    ]
    p = _run(cmd, check=False)
    raw = (p.stdout or "").strip()
    if p.returncode != 0:
        raise RuntimeError(
            f"curl failed ({p.returncode}):\n{p.stderr}\nstdout:\n{p.stdout}"
        )
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        raise RuntimeError(f"Non-JSON response from {path}:\n{raw[:2000]}")


def _extract_final_video(resp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Support multiple shapes:
      A) {"final_video": {...}}
      B) {"outputs": {"final_video": {...}}}
      C) {"finalVideo": {...}}
      D) {"outputs": {"finalVideo": {...}}}
    """
    if isinstance(resp.get("final_video"), dict):
        return resp["final_video"]  # type: ignore[return-value]
    if isinstance(resp.get("finalVideo"), dict):
        return resp["finalVideo"]  # type: ignore[return-value]

    outs = resp.get("outputs")
    if isinstance(outs, dict):
        if isinstance(outs.get("final_video"), dict):
            return outs["final_video"]  # type: ignore[return-value]
        if isinstance(outs.get("finalVideo"), dict):
            return outs["finalVideo"]  # type: ignore[return-value]

    return {}


def _ffprobe_format_duration(video_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-hide_banner",
        "-loglevel",
        "error",
        "-show_format",
        "-of",
        "json",
        str(video_path),
    ]
    p = _run(cmd, check=True)
    data = json.loads(p.stdout or "{}")
    fmt = data.get("format", {}) or {}
    try:
        return float(fmt.get("duration") or 0.0)
    except Exception:
        return 0.0


def _ffprobe_audio_stream_count(video_path: Path) -> int:
    cmd = [
        "ffprobe",
        "-hide_banner",
        "-loglevel",
        "error",
        "-select_streams",
        "a",
        "-show_streams",
        "-of",
        "json",
        str(video_path),
    ]
    p = _run(cmd, check=True)
    data = json.loads(p.stdout or "{}")
    streams = data.get("streams", []) or []
    return len(streams)


_SRT_TS_RE = re.compile(
    r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)"
)


def _srt_last_end_sec(srt_text: str) -> float:
    last = 0.0
    for m in _SRT_TS_RE.finditer(srt_text):
        eh, em, es, ems = m.group(5), m.group(6), m.group(7), m.group(8)
        sec = int(eh) * 3600 + int(em) * 60 + int(es) + int(ems) / 1000.0
        if sec > last:
            last = sec
    return last


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _build_run_payload(case: CaseConfig, session_id: str, topic: str) -> Dict[str, Any]:
    steps = [
        {"name": "story"},
        {"name": "storyboard"},
        {"name": "image_prompts"},
        {"name": "image_assets"},
        {"name": "video_prompts"},
    ]

    # ✅ 只有在需要“有声+旁白”的 case 才跑音频链路
    if case.audio_enabled and case.voiceover_enabled:
        steps += [
            {"name": "dialogue_script"},
            {"name": "audio_segments"},
            {"name": "narration"},
        ]

    # subtitles：两种 case 都要（silent 也可以有字幕）
    if case.subtitle_enabled:
        steps.append({"name": "subtitles"})

    steps += [
        {"name": "render_plan"},
        {"name": "final_video"},
    ]

    return {
        "workflow_id": "storybook-demo",
        "session_id": session_id,
        "input": {
            "topic": topic,
            "render_mode": case.render_mode,
            "audio_enabled": case.audio_enabled,
            "voiceover_enabled": case.voiceover_enabled,
            "subtitle_enabled": case.subtitle_enabled,
            "video_provider": "mock",
            "language": "zh-CN",
            "audience": "children",
            "tone": "warm",
            "visual_style": "storybook",
            "character_style": "animal",
            "voice_style": "warm_female",
            "voice_mode": "single",
            "duration_sec": 60,
            "output_mode": "full_video",
            "structured_characters_enabled": False,
            "character_ids": [],
        },
        "steps": steps,
    }


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _ensure_image_assets(
    api_base: str, run_data: Dict[str, Any], workflow_input: Dict[str, Any]
) -> Dict[str, Any]:
    """
    image_assets is deferred in runner; refresh may return pending/retrying/0 assets.
    We poll refresh until assets are ready (asset_count >= scene_count) or timeout.
    """
    run_id = str(run_data["run_id"])
    _ensure_dir(REPO_ROOT / "assets" / "mock" / "image" / run_id)

    storyboard = (run_data.get("outputs", {}) or {}).get("storyboard", {}) or {}
    scenes = storyboard.get("scenes") or []
    scene_count = len(scenes) if isinstance(scenes, list) else 0
    min_expected = max(1, scene_count)

    refresh_req = {
        "workflow_id": run_data.get("workflow_id") or "storybook-demo",
        "session_id": run_data.get("session_id"),
        "run_id": run_id,
        "storyboard": storyboard,
        # ✅ IMPORTANT: must pass workflow_input with topic
        "workflow_input": workflow_input,
        "image_review": (run_data.get("outputs", {}) or {}).get("image_review", {})
        or {},
        "video_provider": workflow_input.get("video_provider", "mock"),
    }

    max_attempts = int(os.environ.get("ACCEPTANCE_REFRESH_ATTEMPTS", "12"))
    sleep_sec = float(os.environ.get("ACCEPTANCE_REFRESH_SLEEP_SEC", "5"))

    last_assets: Dict[str, Any] = {}
    for attempt in range(1, max_attempts + 1):
        resp = _curl_json(
            api_base, "/v1/image-review/refresh", refresh_req, timeout_sec=300
        )
        assets = resp.get("image_assets", {}) or {}
        last_assets = assets

        status = str(assets.get("status") or "").strip().lower()
        asset_count = int(assets.get("asset_count") or 0)

        print(
            f"refresh attempt {attempt}/{max_attempts}: status={status or 'n/a'} asset_count={asset_count}/{min_expected}"
        )

        if asset_count >= min_expected and status not in {"pending", "retrying"}:
            return assets

        time.sleep(sleep_sec)

    raise AssertionError(
        f"image_assets not generated after {max_attempts} attempts "
        f"(expected>={min_expected}, got={int(last_assets.get('asset_count') or 0)}, status={last_assets.get('status')})"
    )


def _render_final(
    api_base: str,
    run_data: Dict[str, Any],
    workflow_input: Dict[str, Any],
    image_assets: Dict[str, Any],
) -> Dict[str, Any]:
    subtitles = (run_data.get("outputs", {}) or {}).get("subtitles", {}) or {}
    render_req = {
        "workflow_id": run_data.get("workflow_id") or "storybook-demo",
        "session_id": run_data.get("session_id"),
        "run_id": str(run_data["run_id"]),
        # ✅ IMPORTANT: must pass workflow_input with topic
        "workflow_input": workflow_input,
        "image_assets": image_assets,
        "audio_segments": (run_data.get("outputs", {}) or {}).get("audio_segments", {})
        or {},
        "subtitles": subtitles if isinstance(subtitles, dict) else {"srt_preview": ""},
    }
    resp = _curl_json(api_base, "/v1/final-video/render", render_req, timeout_sec=300)

    fv = _extract_final_video(resp)
    if not fv:
        raise AssertionError(
            "final_video missing in /v1/final-video/render response.\n"
            f"response keys={list(resp.keys())}\n"
            f"response preview:\n{json.dumps(resp, ensure_ascii=False, indent=2)[:2000]}"
        )
    return fv


def _case_run(api_base: str, case: CaseConfig, idx: int) -> None:
    session_id = f"acceptance-{case.name}-{int(time.time())}-{idx}"
    topic = f"acceptance {case.name} audio={case.audio_enabled} voiceover={case.voiceover_enabled}"
    payload = _build_run_payload(case, session_id, topic)
    workflow_input = payload["input"]  # ✅ keep original input (contains topic)

    print(f"\n=== RUN CASE: {case.name} ===")
    run_data = _curl_json(api_base, "/v1/workflow/run", payload, timeout_sec=300)
    run_id = str(run_data.get("run_id") or "")
    _assert(run_id.startswith("run_"), f"invalid run_id: {run_id}")
    print("run_id:", run_id)

    image_assets = _ensure_image_assets(api_base, run_data, workflow_input)
    final_video = _render_final(api_base, run_data, workflow_input, image_assets)

    status = str(final_video.get("status") or "").lower()
    _assert(
        status == "generated",
        f"final_video not generated (status={status}, final_video={final_video})",
    )

    video_dir = VIDEO_ROOT / run_id
    mp4 = video_dir / "final.mp4"
    srt = video_dir / "subtitles.srt"

    _assert(mp4.exists(), f"final.mp4 missing: {mp4}")
    _assert(mp4.stat().st_size > 50_000, f"final.mp4 too small: {mp4.stat().st_size}")

    audio_cnt = _ffprobe_audio_stream_count(mp4)
    if case.audio_enabled and case.voiceover_enabled:
        _assert(audio_cnt >= 1, f"expected audio stream, got {audio_cnt}")
    else:
        _assert(audio_cnt == 0, f"expected NO audio stream, got {audio_cnt}")

    if case.subtitle_enabled:
        _assert(srt.exists(), f"subtitles.srt missing: {srt}")
        srt_txt = srt.read_text(encoding="utf-8", errors="ignore")
        _assert(len(srt_txt.strip()) > 0, "subtitles.srt empty")

        dur = _ffprobe_format_duration(mp4)
        last_end = _srt_last_end_sec(srt_txt)
        _assert(
            last_end <= dur + 0.35,
            f"SRT end time exceeds video duration (last_end={last_end:.3f}, dur={dur:.3f})",
        )

    print(
        "OK:",
        f"audio_streams={audio_cnt}",
        f"subtitles={'on' if case.subtitle_enabled else 'off'}",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--api-base", default=os.environ.get("API_BASE_URL", "http://127.0.0.1:8004")
    )
    args = ap.parse_args()

    api_base = str(args.api_base).rstrip("/")
    cases = [
        CaseConfig(
            name="silent_subtitles",
            audio_enabled=False,
            voiceover_enabled=False,
            subtitle_enabled=True,
            render_mode="auto",
        ),
        CaseConfig(
            name="audio_voiceover_subtitles",
            audio_enabled=True,
            voiceover_enabled=True,
            subtitle_enabled=True,
            render_mode="auto",
        ),
    ]

    try:
        for i, case in enumerate(cases, 1):
            _case_run(api_base, case, i)
        print("\nALL ACCEPTANCE CHECKS PASSED ✅")
        return 0
    except Exception as e:
        print("\nACCEPTANCE FAILED ❌")
        print(str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
