from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.image_candidate_selector import select_best_candidate


def _write_candidate(path: Path, color: tuple[int, int, int]) -> None:
    try:
        from PIL import Image

        image = Image.new("RGB", (640, 640), color)
        image.save(path)
    except Exception:
        path.write_bytes(b"candidate")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        first = tmp_dir / "scene_01__candidate_a.png"
        second = tmp_dir / "scene_01__candidate_b.png"
        _write_candidate(first, (245, 245, 240))
        _write_candidate(second, (120, 180, 120))

        characters = [
            {
                "display_name": "小兔子",
                "species": "rabbit",
                "visual_traits": "small white rabbit, long upright rabbit ears",
                "forbidden_traits": ["no turtle shell"],
            },
            {
                "display_name": "小乌龟",
                "species": "turtle",
                "visual_traits": "small green turtle, round turtle shell",
                "forbidden_traits": ["no rabbit ears"],
            },
        ]

        result = select_best_candidate(
            candidate_asset_refs=[
                {"file_name": first.name, "local_path": str(first)},
                {"file_name": second.name, "local_path": str(second)},
            ],
            prompt="required scene characters: 小兔子 and 小乌龟",
            characters=characters,
        )

        weak_first = tmp_dir / "scene_02__candidate_a.png"
        strong_second = tmp_dir / "scene_02__candidate_b.png"
        _write_candidate(weak_first, (20, 20, 20))
        _write_candidate(strong_second, (245, 245, 240))

        second_result = select_best_candidate(
            candidate_asset_refs=[
                {"file_name": weak_first.name, "local_path": str(weak_first)},
                {"file_name": strong_second.name, "local_path": str(strong_second)},
            ],
            prompt="required scene characters: 小兔子",
            characters=[
                {
                    "display_name": "小兔子",
                    "species": "rabbit",
                    "visual_traits": "small white rabbit, soft white fur",
                    "forbidden_traits": [],
                }
            ],
        )

    quality_gates = result.get("quality_gates") or {}
    candidate_scores = result.get("candidate_scores") or []
    failures: list[str] = []

    print("selection_source =", result.get("selection_source"))
    print("quality_gates =", quality_gates)
    print("candidate_scores_count =", len(candidate_scores))
    print(
        "second_selected_file =",
        (second_result.get("selected_asset_ref") or {}).get("file_name"),
    )

    if result.get("selection_source") != "auto_filter":
        failures.append("selection_source should remain auto_filter")
    if result.get("review_required") is True:
        failures.append("auto mode quality gates should not require manual review")
    if quality_gates.get("multi_character_scene") is not True:
        failures.append("quality gate should identify multi-character scene")
    if quality_gates.get("advisory_only") is not True:
        failures.append("quality gate should be advisory-only in auto mode")
    if quality_gates.get("visual_verifier_available") is not False:
        failures.append("quality gate should state visual verifier is unavailable")
    for label in ["小兔子", "小乌龟"]:
        if label not in quality_gates.get("required_character_labels", []):
            failures.append(f"quality gate missing required label {label}")
    if not candidate_scores:
        failures.append("candidate_scores should be present")
    for score in candidate_scores:
        score_gates = score.get("quality_gates") or {}
        if score_gates.get("multi_character_scene") is not True:
            failures.append("candidate score missing multi-character quality gate")

    second_selected = second_result.get("selected_asset_ref") or {}
    if second_selected.get("file_name") != "scene_02__candidate_b.png":
        failures.append("selector should choose higher-scored candidate_b when it wins")

    if failures:
        print("SUMMARY = FAIL")
        for failure in failures:
            print("-", failure)
        return 1

    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
