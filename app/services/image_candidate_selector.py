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


def _character_label(item: Dict[str, Any]) -> str:
    return (
        str(item.get("display_name") or "").strip()
        or str(item.get("species") or "").strip()
        or str(item.get("character_id") or "").strip()
    )


def _required_character_labels(characters: List[Dict[str, Any]]) -> List[str]:
    labels: List[str] = []
    for item in characters or []:
        if not isinstance(item, dict):
            continue
        label = _character_label(item)
        if label and label not in labels:
            labels.append(label)
    return labels


def _quality_gates(characters: List[Dict[str, Any]]) -> Dict[str, Any]:
    labels = _required_character_labels(characters)
    multi_character_scene = len(labels) >= 2
    risk_reasons: List[str] = []

    if multi_character_scene:
        risk_reasons.extend(
            [
                "multi_character_scene",
                "metadata_only_candidate_filter",
                "visual_verifier_not_available",
            ]
        )

    return {
        "required_character_labels": labels,
        "multi_character_scene": multi_character_scene,
        "visual_verifier_available": False,
        "advisory_only": True,
        "risk_reasons": risk_reasons,
    }


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


def _extract_forbidden_colors(characters: List[Dict[str, Any]]) -> List[str]:
    texts: List[str] = []
    for item in characters or []:
        if not isinstance(item, dict):
            continue

        value = item.get("forbidden_traits")
        if isinstance(value, list):
            texts.extend(str(x or "") for x in value)
        else:
            texts.append(str(value or ""))

    haystack = " | ".join(texts).lower()
    found: List[str] = []
    for color_name, aliases in COLOR_KEYWORDS.items():
        if any(alias.lower() in haystack for alias in aliases):
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


def _subject_region_pixels(img: Any) -> List[tuple[int, int, int]]:
    if Image is None:
        return []

    image = img.convert("RGB")
    width, height = image.size

    # Focus on the likely subject area instead of the full background.
    # This avoids counting sky / grass / warm lighting as the character's color.
    left = int(width * 0.08)
    right = int(width * 0.92)
    top = int(height * 0.18)
    bottom = int(height * 0.92)

    if right > left and bottom > top:
        image = image.crop((left, top, right, bottom))

    image = image.resize((96, 96))
    return list(image.getdata())


def _color_rules() -> Dict[str, Any]:
    return {
        "white": lambda r, g, b: min(r, g, b) > 175 and max(abs(r-g), abs(g-b), abs(r-b)) < 55,
        "red": lambda r, g, b: r > 145 and g < 135 and b < 135 and r > g * 1.15 and r > b * 1.15,
        "green": lambda r, g, b: g > 120 and r < 175 and b < 175 and g > r * 1.08,
        "blue": lambda r, g, b: b > 120 and r < 170 and g < 185 and b > r * 1.08,
        "yellow": lambda r, g, b: r > 150 and g > 135 and b < 135,
        "orange": lambda r, g, b: r > 165 and 65 < g < 185 and b < 135,
        "pink": lambda r, g, b: r > 170 and g > 105 and b > 125,
        "purple": lambda r, g, b: r > 105 and b > 120 and g < 145,
        "brown": lambda r, g, b: r > 85 and 45 < g < 145 and b < 115,
        "black": lambda r, g, b: max(r, g, b) < 75,
        "gray": lambda r, g, b: 60 < r < 205 and abs(r-g) < 24 and abs(g-b) < 24,
    }


def _color_ratios(img: Any, colors: List[str]) -> Dict[str, float]:
    if Image is None:
        return {}

    pixels = _subject_region_pixels(img)
    total = max(1, len(pixels))
    rules = _color_rules()

    ratios: Dict[str, float] = {}
    for color_name in colors:
        predicate = rules.get(color_name)
        if predicate is None:
            continue

        count = 0
        for r, g, b in pixels:
            if predicate(r, g, b):
                count += 1

        ratios[color_name] = round(count / total, 4)

    return ratios


def _color_hits(
    img: Any,
    expected_colors: List[str],
    *,
    threshold: float = 0.035,
) -> Tuple[List[str], Dict[str, float]]:
    ratios = _color_ratios(img, expected_colors)
    hits = [
        color_name
        for color_name, ratio in ratios.items()
        if ratio >= threshold
    ]
    return hits, ratios

def _score_candidate(
    candidate: Dict[str, Any],
    *,
    prompt: str,
    characters: List[Dict[str, Any]],
    quality_gates: Dict[str, Any],
) -> Dict[str, Any]:
    path = _candidate_path(candidate)
    reasons: List[str] = []
    score = 0.0
    expected_colors = _extract_expected_colors(prompt, characters)
    forbidden_colors = _extract_forbidden_colors(characters)

    if not path.exists():
        return {
            "asset_ref": dict(candidate),
            "score": 0.0,
            "passed": False,
            "reasons": ["file_missing"],
            "expected_colors": expected_colors,
            "matched_colors": [],
            "color_ratios": {},
            "quality_gates": quality_gates,
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
    forbidden_matched_colors: List[str] = []
    forbidden_color_ratios: Dict[str, float] = {}

    if image is not None and expected_colors:
        matched_colors, color_ratios = _color_hits(
            image,
            expected_colors,
            threshold=0.035,
        )

        if matched_colors:
            expected_strength = sum(color_ratios.get(color, 0.0) for color in matched_colors)
            color_score = min(expected_strength * 180.0, 30.0)
            score += color_score
            reasons.append("matched_colors:" + ",".join(matched_colors))
            reasons.append(f"expected_color_strength:{expected_strength:.4f}")
        else:
            score -= 18.0
            reasons.append("matched_colors:none")
            reasons.append("expected_color_missing_penalty")

    elif not expected_colors:
        score += 2.0
        reasons.append("no_expected_colors_found_in_character_profile")

    if image is not None and forbidden_colors:
        forbidden_matched_colors, forbidden_color_ratios = _color_hits(
            image,
            forbidden_colors,
            threshold=0.06,
        )

        if forbidden_matched_colors:
            forbidden_strength = sum(
                forbidden_color_ratios.get(color, 0.0)
                for color in forbidden_matched_colors
            )
            penalty = min(forbidden_strength * 120.0, 24.0)
            score -= penalty
            reasons.append("forbidden_colors:" + ",".join(forbidden_matched_colors))
            reasons.append(f"forbidden_color_penalty:{penalty:.1f}")

    if quality_gates.get("multi_character_scene"):
        reasons.append("metadata_quality_gate_multi_character_scene")

    passed = score >= MIN_PASS_SCORE

    return {
        "asset_ref": dict(candidate),
        "score": round(score, 2),
        "passed": passed,
        "reasons": reasons,
        "expected_colors": expected_colors,
        "matched_colors": matched_colors,
        "color_ratios": color_ratios,
        "forbidden_colors": forbidden_colors,
        "forbidden_matched_colors": forbidden_matched_colors,
        "forbidden_color_ratios": forbidden_color_ratios,
        "quality_gates": quality_gates,
    }


def select_best_candidate(
    *,
    candidate_asset_refs: List[Dict[str, Any]],
    prompt: str,
    characters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    scored: List[Dict[str, Any]] = []
    quality_gates = _quality_gates(characters)

    for candidate in candidate_asset_refs or []:
        if not isinstance(candidate, dict):
            continue
        score_item = _score_candidate(
            candidate,
            prompt=prompt,
            characters=characters,
            quality_gates=quality_gates,
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
                "quality_gates": item.get("quality_gates") or {},
            }
            for item in scored
        ],
        "candidate_asset_refs": [dict(item.get("asset_ref") or {}) for item in scored],
        "best_score": best_score,
        "should_retry": best_score < MIN_PASS_SCORE,
        "quality_gates": quality_gates,
        "review_required": False,
    }
