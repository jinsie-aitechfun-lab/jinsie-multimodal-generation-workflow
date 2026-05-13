from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from PIL import Image, ImageStat
except Exception:  # pragma: no cover
    Image = None
    ImageStat = None


COLOR_KEYWORDS = {
    "white": ["white", "白", "white fur", "soft white fur", "白色", "白毛"],
    "red": ["red", "红", "red scarf", "红围巾", "红色"],
    "green": ["green", "绿", "green shell", "绿色", "绿壳"],
    "blue": ["blue", "蓝", "蓝色"],
    "yellow": ["yellow", "黄", "黄色"],
    "orange": ["orange", "橙", "橙色"],
    "pink": ["pink", "粉", "粉色"],
    "purple": ["purple", "紫", "紫色"],
    "brown": ["brown", "棕", "棕色", "咖啡色"],
    "black": ["black", "黑", "黑色"],
    "gray": ["gray", "grey", "灰", "灰色"],
}

MIN_PASS_SCORE = 45.0


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _extract_positive_texts(prompt: str, characters: List[Dict[str, Any]]) -> List[str]:
    texts: List[str] = [str(prompt or "")]
    for item in characters or []:
        if not isinstance(item, dict):
            continue

        # Only positive identity fields should define expected colors.
        # Do not read forbidden_traits here, otherwise "blue car" in "must avoid"
        # will be incorrectly treated as an expected color.
        for key in [
            "display_name",
            "species",
            "visual_traits",
            "signature_traits",
            "visual_identity",
            "required_presence_rules",
        ]:
            value = item.get(key)
            if isinstance(value, list):
                texts.extend(str(x or "") for x in value)
            else:
                texts.append(str(value or ""))

    return texts


def _extract_expected_colors(prompt: str, characters: List[Dict[str, Any]]) -> List[str]:
    # Expected character colors must come from the fixed character profile,
    # not from the full scene prompt. The scene prompt may contain background
    # colors or negative constraints such as "blue car" / "green car", which
    # should not become expected colors.
    character_texts = _extract_positive_texts("", characters)
    haystack = " | ".join(character_texts).lower()

    found: List[str] = []
    for color_name, aliases in COLOR_KEYWORDS.items():
        if any(alias.lower() in haystack for alias in aliases):
            found.append(color_name)

    # Only fall back to prompt text when no character profile is available.
    if found or character_texts:
        return found

    prompt_haystack = str(prompt or "").lower()
    for color_name, aliases in COLOR_KEYWORDS.items():
        if any(alias.lower() in prompt_haystack for alias in aliases):
            found.append(color_name)

    return found


def _candidate_path(candidate: Dict[str, Any]) -> Path:
    raw_path = (
        candidate.get("path")
        or candidate.get("local_path")
        or candidate.get("file_path")
        or candidate.get("relative_path")
        or ""
    )
    path = Path(str(raw_path))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _color_hits(img: Any, expected_colors: List[str]) -> Tuple[List[str], Dict[str, float]]:
    if Image is None:
        return [], {}

    image = img.convert("RGB").resize((96, 96))
    pixels = list(image.getdata())
    total = max(1, len(pixels))

    def ratio(predicate) -> float:
        count = 0
        for r, g, b in pixels:
            if predicate(r, g, b):
                count += 1
        return count / total

    rules = {
        "white": lambda r, g, b: min(r, g, b) > 175 and max(abs(r-g), abs(g-b), abs(r-b)) < 55,
        "red": lambda r, g, b: r > 150 and g < 120 and b < 120,
        "green": lambda r, g, b: g > 120 and r < 170 and b < 170,
        "blue": lambda r, g, b: b > 130 and r < 150 and g < 170,
        "yellow": lambda r, g, b: r > 150 and g > 140 and b < 130,
        "orange": lambda r, g, b: r > 170 and 70 < g < 180 and b < 130,
        "pink": lambda r, g, b: r > 170 and g > 110 and b > 130,
        "purple": lambda r, g, b: r > 110 and b > 120 and g < 140,
        "brown": lambda r, g, b: r > 90 and 50 < g < 140 and b < 110,
        "black": lambda r, g, b: max(r, g, b) < 70,
        "gray": lambda r, g, b: 60 < r < 200 and abs(r-g) < 20 and abs(g-b) < 20,
    }

    ratios: Dict[str, float] = {}
    hits: List[str] = []

    for color_name in expected_colors:
        predicate = rules.get(color_name)
        if predicate is None:
            continue
        value = ratio(predicate)
        ratios[color_name] = round(value, 4)
        if value >= 0.02:
            hits.append(color_name)

    return hits, ratios


def _score_candidate(
    candidate: Dict[str, Any],
    *,
    prompt: str,
    characters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    path = _candidate_path(candidate)
    reasons: List[str] = []
    score = 0.0
    expected_colors = _extract_expected_colors(prompt, characters)

    if not path.exists():
        return {
            "asset_ref": dict(candidate),
            "score": 0.0,
            "passed": False,
            "reasons": ["file_missing"],
            "expected_colors": expected_colors,
            "matched_colors": [],
            "color_ratios": {},
        }

    score += 20.0
    reasons.append("file_exists")

    image = None
    width = 0
    height = 0
    contrast_bonus = 0.0

    if Image is not None:
        try:
            image = Image.open(path)
            width, height = image.size
            score += 10.0
            reasons.append(f"image_readable:{width}x{height}")

            area = width * height
            if area >= 512 * 512:
                score += 5.0
                reasons.append("area_ok")

            if ImageStat is not None:
                stat = ImageStat.Stat(image.convert("RGB"))
                std_values = stat.stddev or [0.0, 0.0, 0.0]
                contrast_bonus = min(sum(std_values) / 3.0 / 12.0, 10.0)
                if contrast_bonus > 0:
                    score += contrast_bonus
                    reasons.append(f"contrast_bonus:{contrast_bonus:.1f}")

        except Exception as error:  # pragma: no cover
            reasons.append(f"image_open_error:{type(error).__name__}")

    matched_colors: List[str] = []
    color_ratios: Dict[str, float] = {}

    if image is not None and expected_colors:
        matched_colors, color_ratios = _color_hits(image, expected_colors)
        if matched_colors:
            color_score = min(len(matched_colors) * 8.0, 24.0)
            score += color_score
            reasons.append("matched_colors:" + ",".join(matched_colors))
        else:
            reasons.append("matched_colors:none")
    elif not expected_colors:
        score += 5.0
        reasons.append("no_expected_colors_found_in_prompt")

    file_name = str(candidate.get("file_name") or "")
    if "candidate_a" in file_name:
        score += 0.5
        reasons.append("stable_tiebreak_candidate_a")

    passed = score >= MIN_PASS_SCORE

    return {
        "asset_ref": dict(candidate),
        "score": round(score, 2),
        "passed": passed,
        "reasons": reasons,
        "expected_colors": expected_colors,
        "matched_colors": matched_colors,
        "color_ratios": color_ratios,
    }


def select_best_candidate(
    *,
    candidate_asset_refs: List[Dict[str, Any]],
    prompt: str,
    characters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    scored: List[Dict[str, Any]] = []

    for candidate in candidate_asset_refs or []:
        if not isinstance(candidate, dict):
            continue
        score_item = _score_candidate(
            candidate,
            prompt=prompt,
            characters=characters,
        )
        enriched_ref = dict(candidate)
        enriched_ref["auto_filter_score"] = score_item["score"]
        enriched_ref["auto_filter_passed"] = score_item["passed"]
        enriched_ref["auto_filter_reasons"] = score_item["reasons"]
        score_item["asset_ref"] = enriched_ref
        scored.append(score_item)

    if not scored:
        raise ValueError("candidate_asset_refs is empty")

    scored.sort(
        key=lambda item: (
            float(item.get("score") or 0.0),
            1 if "candidate_a" in str(item.get("asset_ref", {}).get("file_name") or "") else 0,
        ),
        reverse=True,
    )

    best = scored[0]
    best_score = float(best.get("score") or 0.0)
    best_ref = dict(best.get("asset_ref") or {})
    selection_reason = (
        f"auto_filter selected {best_ref.get('file_name') or 'unknown'} "
        f"score={best_score:.2f}; "
        + "; ".join(best.get("reasons") or [])
    )
    best_ref["selection_source"] = "auto_filter"
    best_ref["selection_reason"] = selection_reason

    return {
        "selected_asset_ref": best_ref,
        "selection_source": "auto_filter",
        "selection_reason": selection_reason,
        "candidate_scores": [
            {
                "file_name": str(item.get("asset_ref", {}).get("file_name") or ""),
                "score": item.get("score"),
                "passed": item.get("passed"),
                "reasons": item.get("reasons") or [],
                "expected_colors": item.get("expected_colors") or [],
                "matched_colors": item.get("matched_colors") or [],
                "color_ratios": item.get("color_ratios") or {},
            }
            for item in scored
        ],
        "candidate_asset_refs": [dict(item.get("asset_ref") or {}) for item in scored],
        "best_score": best_score,
        "should_retry": best_score < MIN_PASS_SCORE,
    }
