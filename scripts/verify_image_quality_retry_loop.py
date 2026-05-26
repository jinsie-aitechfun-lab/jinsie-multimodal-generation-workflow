from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.image_candidate_selector import MIN_PASS_SCORE, select_best_candidate
from app.services.image_quality_retry_policy import (
    derive_retry_prompt_amendment,
    quality_max_retries,
    summarize_selection_for_history,
)


def _write_candidate(path: Path, color: tuple[int, int, int]) -> None:
    try:
        from PIL import Image

        image = Image.new("RGB", (640, 640), color)
        image.save(path)
    except Exception:
        path.write_bytes(b"candidate")


def _both_failing_verifier(*, image_path: Path, prompt: str, characters: list[dict]) -> dict:
    return {
        "score": 20,
        "passed": False,
        "missing_required_characters": ["小乌龟"],
        "forbidden_trait_issues": ["turtle with rabbit ears"],
        "anatomy_leakage_issues": ["rabbit/turtle body part blending"],
        "notes": "both candidates fail",
    }


def _all_passing_verifier(*, image_path: Path, prompt: str, characters: list[dict]) -> dict:
    return {
        "score": 82,
        "passed": True,
        "missing_required_characters": [],
        "forbidden_trait_issues": [],
        "anatomy_leakage_issues": [],
        "notes": "both clean",
    }


def test_amendment_includes_required_characters() -> list[str]:
    failures: list[str] = []
    amendment = derive_retry_prompt_amendment(
        base_prompt="forest scene with rabbit and turtle",
        base_negative_prompt="low quality, blurry",
        visual_review={
            "missing_required_characters": ["小乌龟"],
            "forbidden_trait_issues": [],
            "anatomy_leakage_issues": [],
        },
        attempt=2,
    )
    if not amendment.get("has_amendments"):
        failures.append("amendment should set has_amendments=true when characters are missing")
    if "小乌龟" not in amendment.get("prompt", ""):
        failures.append("missing character name should be injected into the next-attempt prompt")
    if "CRITICAL" not in amendment.get("prompt", ""):
        failures.append("missing-character constraint should be prefixed with CRITICAL")
    if amendment.get("negative_prompt") != "low quality, blurry":
        failures.append("negative_prompt should be unchanged when only missing-character signal present")
    return failures


def test_amendment_appends_negatives() -> list[str]:
    failures: list[str] = []
    amendment = derive_retry_prompt_amendment(
        base_prompt="forest scene",
        base_negative_prompt="low quality",
        visual_review={
            "missing_required_characters": [],
            "forbidden_trait_issues": ["rabbit with turtle shell"],
            "anatomy_leakage_issues": ["fused rabbit-turtle creature"],
        },
        attempt=2,
    )
    negative = amendment.get("negative_prompt", "")
    if "rabbit with turtle shell" not in negative:
        failures.append("forbidden trait should be appended to negative_prompt")
    if "fused rabbit-turtle creature" not in negative:
        failures.append("anatomy leakage should be appended to negative_prompt")
    if not negative.startswith("low quality"):
        failures.append("existing negative_prompt should be preserved as the prefix")
    reasons = amendment.get("amendment_reasons") or []
    if not any("forbidden:" in r for r in reasons):
        failures.append("amendment_reasons should tag forbidden issues")
    if not any("anatomy:" in r for r in reasons):
        failures.append("amendment_reasons should tag anatomy issues")
    return failures


def test_amendment_no_changes_when_clean() -> list[str]:
    failures: list[str] = []
    amendment = derive_retry_prompt_amendment(
        base_prompt="forest scene",
        base_negative_prompt="low quality",
        visual_review={
            "missing_required_characters": [],
            "forbidden_trait_issues": [],
            "anatomy_leakage_issues": [],
        },
        attempt=2,
    )
    if amendment.get("has_amendments"):
        failures.append("amendment should be empty when visual_review has no structured issues")
    if amendment.get("prompt") != "forest scene":
        failures.append("prompt should be unchanged when there is nothing to amend")
    if amendment.get("negative_prompt") != "low quality":
        failures.append("negative_prompt should be unchanged when there is nothing to amend")
    return failures


def test_max_retries_env_override() -> list[str]:
    failures: list[str] = []
    os.environ["IMAGE_QUALITY_MAX_RETRIES"] = "3"
    if quality_max_retries() != 3:
        failures.append(f"env override to 3 should yield 3, got {quality_max_retries()}")

    os.environ["IMAGE_QUALITY_MAX_RETRIES"] = "99"
    if quality_max_retries() != 5:
        failures.append(f"env override should clamp to MAX_ALLOWED_RETRIES=5, got {quality_max_retries()}")

    os.environ["IMAGE_QUALITY_MAX_RETRIES"] = "not-a-number"
    if quality_max_retries() != 2:
        failures.append(f"non-numeric env should fall back to default 2, got {quality_max_retries()}")

    os.environ.pop("IMAGE_QUALITY_MAX_RETRIES", None)
    if quality_max_retries() != 2:
        failures.append(f"unset env should yield default 2, got {quality_max_retries()}")
    return failures


def test_selector_should_retry_on_both_failing() -> list[str]:
    failures: list[str] = []
    os.environ["IMAGE_REVIEW_VISION_ENABLED"] = "false"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        first = tmp_dir / "scene_01__candidate_a.png"
        second = tmp_dir / "scene_01__candidate_b.png"
        _write_candidate(first, (245, 245, 240))
        _write_candidate(second, (245, 245, 240))

        result = select_best_candidate(
            candidate_asset_refs=[
                {"file_name": first.name, "local_path": str(first)},
                {"file_name": second.name, "local_path": str(second)},
            ],
            prompt="required scene characters: 小兔子 and 小乌龟",
            characters=[
                {"display_name": "小兔子", "species": "rabbit"},
                {"display_name": "小乌龟", "species": "turtle"},
            ],
            visual_verifier=_both_failing_verifier,
        )

    best_score = float(result.get("best_score") or 0.0)
    if not result.get("should_retry"):
        failures.append(
            f"both-failing candidates should set should_retry=true (best_score={best_score})"
        )
    if best_score >= MIN_PASS_SCORE:
        failures.append(
            f"best_score should be below MIN_PASS_SCORE={MIN_PASS_SCORE} when both candidates fail "
            f"(got {best_score})"
        )
    scores = result.get("candidate_scores") or []
    if scores and scores[0].get("score_mode") != "vision_dominant":
        failures.append(
            f"score_mode should be vision_dominant when verifier ran; got {scores[0].get('score_mode')}"
        )
    if scores and "missing_required_characters" not in (scores[0].get("visual_hard_failures") or []):
        failures.append("visual_hard_failures should record missing_required_characters")
    return failures


def test_selector_no_retry_on_all_passing() -> list[str]:
    failures: list[str] = []
    os.environ["IMAGE_REVIEW_VISION_ENABLED"] = "false"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        first = tmp_dir / "scene_02__candidate_a.png"
        second = tmp_dir / "scene_02__candidate_b.png"
        _write_candidate(first, (245, 245, 240))
        _write_candidate(second, (245, 245, 240))

        result = select_best_candidate(
            candidate_asset_refs=[
                {"file_name": first.name, "local_path": str(first)},
                {"file_name": second.name, "local_path": str(second)},
            ],
            prompt="required scene characters: 小兔子",
            characters=[{"display_name": "小兔子", "species": "rabbit"}],
            visual_verifier=_all_passing_verifier,
        )
    if result.get("should_retry"):
        failures.append("all-passing candidates should NOT trigger should_retry")
    return failures


def test_selector_metadata_only_when_verifier_absent() -> list[str]:
    failures: list[str] = []
    os.environ["IMAGE_REVIEW_VISION_ENABLED"] = "false"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        first = tmp_dir / "scene_03__candidate_a.png"
        second = tmp_dir / "scene_03__candidate_b.png"
        _write_candidate(first, (245, 245, 240))
        _write_candidate(second, (245, 245, 240))
        result = select_best_candidate(
            candidate_asset_refs=[
                {"file_name": first.name, "local_path": str(first)},
                {"file_name": second.name, "local_path": str(second)},
            ],
            prompt="forest",
            characters=[{"display_name": "小兔子", "species": "rabbit"}],
            visual_verifier=None,
        )
    scores = result.get("candidate_scores") or []
    if scores and scores[0].get("score_mode") != "metadata_only":
        failures.append(
            f"score_mode should be metadata_only when no verifier; got {scores[0].get('score_mode')}"
        )
    return failures


def test_summarize_selection_shape() -> list[str]:
    failures: list[str] = []
    summary = summarize_selection_for_history(
        attempt=2,
        selection={
            "best_score": 88.5,
            "should_retry": False,
            "selected_asset_ref": {"file_name": "scene_01__candidate_b.png"},
        },
        amendment_reasons=["missing:小乌龟"],
    )
    if summary.get("attempt") != 2:
        failures.append("history entry should preserve attempt index")
    if summary.get("selected_file_name") != "scene_01__candidate_b.png":
        failures.append("history entry should expose selected_file_name")
    if summary.get("best_score") != 88.5:
        failures.append("history entry should preserve best_score")
    if summary.get("should_retry") is not False:
        failures.append("history entry should preserve should_retry")
    if summary.get("amendment_reasons") != ["missing:小乌龟"]:
        failures.append("history entry should preserve amendment_reasons list")
    return failures


def main() -> int:
    test_cases = [
        ("amendment_includes_required_characters", test_amendment_includes_required_characters),
        ("amendment_appends_negatives", test_amendment_appends_negatives),
        ("amendment_no_changes_when_clean", test_amendment_no_changes_when_clean),
        ("max_retries_env_override", test_max_retries_env_override),
        ("selector_should_retry_on_both_failing", test_selector_should_retry_on_both_failing),
        ("selector_no_retry_on_all_passing", test_selector_no_retry_on_all_passing),
        ("selector_metadata_only_when_verifier_absent", test_selector_metadata_only_when_verifier_absent),
        ("summarize_selection_shape", test_summarize_selection_shape),
    ]

    all_failures: list[str] = []
    for name, test_fn in test_cases:
        failures = test_fn()
        if failures:
            all_failures.append(f"[{name}]")
            for failure in failures:
                all_failures.append(f"  - {failure}")
            print(f"  {name}: FAIL ({len(failures)})")
        else:
            print(f"  {name}: ok")

    if all_failures:
        print("SUMMARY = FAIL")
        for line in all_failures:
            print(line)
        return 1
    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
