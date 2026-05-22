"""Contract verification for runner refactor Step 16.

Verifies RunnerVoiceSupport keeps voice mode normalization, speaker profile
fallbacks, character speaker detection, and dialogue line payloads stable
while WorkflowRunner delegates through thin wrappers.

Usage:
    python scripts/verify_step16_voice_support.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import StepContext, WorkflowRunner


def make_ctx(**overrides: object) -> StepContext:
    data = {
        "topic": "写一个关于小兔子和小乌龟过河的故事",
        "duration_sec": 60,
        "voice_style": "warm_female",
        "voice_mode": "character",
        "main_character": "little rabbit",
        "main_character_display": "小兔子",
        "secondary_character": "little turtle",
        "secondary_character_display": "小乌龟",
        "speaker_profiles": {
            "narrator": "calm_narrator",
            "mother": "warm_mother",
        },
        "character_speaker_profiles": {
            "narrator": "soft_narrator",
            "main_character": "bright_child",
            "secondary_character": "gentle_elder",
        },
    }
    data.update(overrides)
    return StepContext(
        workflow_id="verify_step16",
        session_id=None,
        run_id="run_verify_step16",
        input=WorkflowInput(**data),
    )


def main() -> int:
    runner = WorkflowRunner()
    support = runner._voice_support
    ctx = make_ctx()

    assert runner._normalized_voice_mode("CHARACTER") == "character"
    assert runner._normalized_voice_mode("bad-mode") == "single"
    assert runner._normalized_voice_mode("multi") == support.normalized_voice_mode(
        "multi"
    )

    speaker_profiles = runner._speaker_profiles(ctx)
    assert speaker_profiles == support.speaker_profiles(ctx)
    assert speaker_profiles == {
        "narrator": "calm_narrator",
        "mother": "warm_mother",
        "child": "gentle_child",
    }

    character_profiles = runner._character_speaker_profiles(ctx)
    assert character_profiles == support.character_speaker_profiles(ctx)
    assert character_profiles == {
        "narrator": "soft_narrator",
        "main_character": "bright_child",
        "secondary_character": "gentle_elder",
    }

    assert runner._character_speaker_name(ctx) == "little_rabbit"
    assert runner._secondary_character_speaker_name(ctx) == "little_turtle"
    assert runner._character_speaker_name(ctx) == support.character_speaker_name(ctx)

    assert runner._detect_character_speaker(ctx, "") == "narrator"
    assert runner._detect_character_speaker(ctx, "在一个温柔的早晨。") == "narrator"
    assert runner._detect_character_speaker(ctx, "故事的主角勇敢出发。") == (
        "main_character"
    )
    assert runner._detect_character_speaker(ctx, "小兔子说：我们走吧。") == (
        "main_character"
    )
    assert runner._detect_character_speaker(ctx, "小乌龟回答：慢慢来。") == (
        "secondary_character"
    )
    assert runner._detect_character_speaker(ctx, "小兔子和小乌龟一起笑了。") == (
        "narrator"
    )
    assert runner._detect_character_speaker(ctx, "有人问：去哪里？") == (
        "main_character"
    )

    resolved_main = runner._resolve_character_speaker(ctx, "小兔子说：我们走吧。")
    assert resolved_main == support.resolve_character_speaker(
        ctx, "小兔子说：我们走吧。"
    )
    assert resolved_main == {
        "speaker": "little_rabbit",
        "voice_style": "bright_child",
    }

    resolved_secondary = runner._resolve_character_speaker(
        ctx, "小乌龟回答：慢慢来。"
    )
    assert resolved_secondary == {
        "speaker": "little_turtle",
        "voice_style": "gentle_elder",
    }

    resolved_narrator = runner._resolve_character_speaker(ctx, "在一个温柔的早晨。")
    assert resolved_narrator == {
        "speaker": "narrator",
        "voice_style": "soft_narrator",
    }

    line = runner._build_dialogue_line(
        line_id="line_01",
        scene_id="scene_01",
        shot_id="shot_01",
        speaker="little_rabbit",
        voice_style="bright_child",
        text="我们走吧。",
    )
    assert line == support.build_dialogue_line(
        line_id="line_01",
        scene_id="scene_01",
        shot_id="shot_01",
        speaker="little_rabbit",
        voice_style="bright_child",
        text="我们走吧。",
    )
    assert line == {
        "line_id": "line_01",
        "speaker": "little_rabbit",
        "voice_style": "bright_child",
        "text": "我们走吧。",
        "scene_id": "scene_01",
        "shot_id": "shot_01",
    }

    line_without_optional_ids = runner._build_dialogue_line(
        line_id="line_02",
        speaker="narrator",
        voice_style="soft_narrator",
        text="旁白。",
    )
    assert "scene_id" not in line_without_optional_ids
    assert "shot_id" not in line_without_optional_ids

    print("[OK] voice mode normalization contract")
    print("[OK] speaker profile fallback contract")
    print("[OK] character speaker detection contract")
    print("[OK] dialogue line payload contract")
    print("PASS: Step 16 voice support contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
