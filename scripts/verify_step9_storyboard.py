"""Contract verification for runner refactor Step 9.

Verifies RunnerStoryboardSupport keeps storyboard, sentence splitting, and
sentence-shot contracts stable while WorkflowRunner delegates through thin
compatibility wrappers.

Usage:
    python scripts/verify_step9_storyboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.workflow import WorkflowInput
from app.services.runner import WorkflowRunner


CHARACTER_MANIFEST = {
    "enabled": True,
    "count": 2,
    "characters": [
        {
            "character_id": "char_primary_01",
            "display_name": "小兔子",
            "species": "小兔子",
            "role_type": "primary",
        },
        {
            "character_id": "char_secondary_01",
            "display_name": "小乌龟",
            "species": "小乌龟",
            "role_type": "secondary",
        },
    ],
}

STORY_TEXT = (
    "在一个安静的早晨，小兔子和小乌龟来到小河边。"
    "它们发现河水有点急，于是停下来一起想办法。"
    "小乌龟找到了一片宽宽的荷叶，小兔子也搬来了细细的树枝。"
    "两个朋友互相鼓励，一点点把小桥搭好。"
    "最后，它们安全过了河，也学会了合作。"
    "夕阳下，它们开心地挥手回家。"
)


def main() -> int:
    runner = WorkflowRunner()
    support = runner._storyboard
    workflow_input = WorkflowInput(
        topic="小兔子和小乌龟一起过河",
        duration_sec=60,
        audio_enabled=False,
    )
    ctx = runner._build_step_context(
        workflow_id="verify-step9",
        session_id="verify-session",
        run_id="run_verify_step9",
        workflow_input=workflow_input,
    )
    outputs = {
        "character_manifest": CHARACTER_MANIFEST,
        "story": {
            "title": "小兔子和小乌龟一起过河的故事",
            "text": STORY_TEXT,
        },
    }

    storyboard = runner._run_storyboard(ctx, outputs)
    direct_storyboard = support.run_storyboard(ctx, outputs)
    assert storyboard == direct_storyboard
    assert storyboard["scene_count"] == 6
    assert storyboard["total_duration_sec"] == 60
    assert len(storyboard["scenes"]) == 6
    assert storyboard["scenes"][0]["scene_id"] == "scene_01"
    assert storyboard["scenes"][0]["duration_sec"] == 10
    assert storyboard["scenes"][0]["characters"] == [
        {
            "character_id": "char_primary_01",
            "display_name": "小兔子",
            "species": "小兔子",
            "role_type": "primary",
        },
        {
            "character_id": "char_secondary_01",
            "display_name": "小乌龟",
            "species": "小乌龟",
            "role_type": "secondary",
        },
    ]

    split = runner._split_story_for_scenes(STORY_TEXT, 6)
    assert split == support.split_story_for_scenes(STORY_TEXT, 6)
    assert len(split) == 6
    assert split[0].endswith("。")

    balanced = runner._split_text_by_char_balance("abcdefghij", 3)
    assert balanced == support.split_text_by_char_balance("abcdefghij", 3)
    assert balanced == ["abc", "def", "ghij"]

    deduped = runner._dedupe_adjacent_text([" A ", "A", "", "B"])
    assert deduped == ["A", "B"]

    sentences = runner._split_story_sentences(
        "第一段故事已经足够完整。第二段故事也足够完整！好。继续"
    )
    assert sentences == ["第一段故事已经足够完整。", "第二段故事也足够完整！好。继续"]
    assert sentences == support.split_story_sentences(
        "第一段故事已经足够完整。第二段故事也足够完整！好。继续"
    )

    sentence_outputs = {"storyboard": storyboard}
    shots = runner._run_sentence_shots(ctx, sentence_outputs)
    direct_shots = support.run_sentence_shots(ctx, sentence_outputs)
    assert shots == direct_shots
    assert shots["enabled"] is True
    assert shots["shot_count"] == 6
    assert shots["items"][0]["shot_id"] == "shot_01"
    assert shots["items"][0]["scene_id"] == "scene_01"
    assert shots["items"][0]["subtitle_text"] == shots["items"][0]["audio_text"]

    print("[OK] storyboard assembly contract")
    print("[OK] story splitting helpers")
    print("[OK] sentence shot contract")
    print("[OK] runner storyboard proxy contract")
    print("PASS: Step 9 storyboard support contract verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
