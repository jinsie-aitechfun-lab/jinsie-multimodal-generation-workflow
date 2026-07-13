from __future__ import annotations

import os
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
    os.environ["IMAGE_REVIEW_VISION_ENABLED"] = "false"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        first = tmp_dir / "scene_01__candidate_a.png"
        second = tmp_dir / "scene_01__candidate_b.png"
        _write_candidate(first, (245, 245, 240))
        _write_candidate(second, (245, 245, 240))

        def fake_visual_verifier(*, image_path: Path, prompt: str, characters: list[dict]) -> dict:
            if image_path.name.endswith("candidate_b.png"):
                return {
                    "score": 94,
                    "passed": True,
                    "missing_required_characters": [],
                    "forbidden_trait_issues": [],
                    "anatomy_leakage_issues": [],
                    "notes": "both required characters are visible and anatomy is clean",
                }
            return {
                "score": 12,
                "passed": False,
                "missing_required_characters": ["小乌龟"],
                "forbidden_trait_issues": ["兔子背着乌龟壳"],
                "anatomy_leakage_issues": ["rabbit/turtle trait leakage"],
                "notes": "candidate lacks a clean turtle and mixes traits",
            }

        result = select_best_candidate(
            candidate_asset_refs=[
                {"file_name": first.name, "local_path": str(first)},
                {"file_name": second.name, "local_path": str(second)},
            ],
            prompt="required scene characters: 小兔子 and 小乌龟",
            characters=[
                {
                    "display_name": "小兔子",
                    "species": "rabbit",
                    "visual_traits": "small white rabbit, long upright ears",
                    "forbidden_traits": ["no turtle shell"],
                },
                {
                    "display_name": "小乌龟",
                    "species": "turtle",
                    "visual_traits": "small green turtle, round shell",
                    "forbidden_traits": ["no rabbit ears"],
                },
            ],
            visual_verifier=fake_visual_verifier,
        )

    selected = result.get("selected_asset_ref") or {}
    candidate_refs = result.get("candidate_asset_refs") or []
    quality_gates = result.get("quality_gates") or {}
    scores = result.get("candidate_scores") or []
    failures: list[str] = []

    print("selected_file =", selected.get("file_name"))
    print("candidate_order =", [item.get("file_name") for item in candidate_refs])
    print("quality_gates =", quality_gates)
    print("candidate_scores =", scores)

    if selected.get("file_name") != "scene_01__candidate_b.png":
        failures.append("visual scoring should select candidate_b")
    if [item.get("file_name") for item in candidate_refs] != [
        "scene_01__candidate_a.png",
        "scene_01__candidate_b.png",
    ]:
        failures.append("candidate_asset_refs should preserve original A/B order")
    if quality_gates.get("visual_verifier_available") is not True:
        failures.append("quality gate should mark visual verifier as available")
    if quality_gates.get("advisory_only") is not False:
        failures.append("quality gate should not be advisory-only when visual verifier is used")
    if not any("visual_score" in " ".join(item.get("reasons") or []) for item in scores):
        failures.append("candidate scores should include visual scoring reasons")
    first_score = next(
        (item for item in scores if item.get("file_name") == "scene_01__candidate_a.png"),
        {},
    )
    first_review = first_score.get("visual_review") or {}
    if first_review.get("passed") is not False:
        failures.append("failed candidate should retain visual_review.passed=false")
    if not first_review.get("missing_required_characters"):
        failures.append("failed candidate should retain missing_required_characters")

    if failures:
        print("SUMMARY = FAIL")
        for failure in failures:
            print("-", failure)
        return 1

    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
