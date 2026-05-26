from __future__ import annotations

import os
from typing import Any, Dict, List


DEFAULT_MAX_RETRIES = 2
MAX_ALLOWED_RETRIES = 5


def quality_max_retries() -> int:
    raw = (os.getenv("IMAGE_QUALITY_MAX_RETRIES") or "").strip()
    if not raw:
        return DEFAULT_MAX_RETRIES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_RETRIES
    return max(0, min(MAX_ALLOWED_RETRIES, value))


def _clean_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    cleaned: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def derive_retry_prompt_amendment(
    *,
    base_prompt: str,
    base_negative_prompt: str,
    visual_review: Dict[str, Any],
    attempt: int,
) -> Dict[str, Any]:
    """Build the next-attempt prompt + negative prompt from the failing visual_review.

    Drives quality-retry: when the vision model flags missing characters,
    forbidden traits, or anatomy leakage, the next generation gets stronger
    positive constraints (e.g. "MUST show 小兔子 and 小乌龟 together") and
    stronger negative constraints (e.g. "rabbit with turtle shell").
    """

    missing = _clean_list(visual_review.get("missing_required_characters"))
    forbidden = _clean_list(visual_review.get("forbidden_trait_issues"))
    anatomy = _clean_list(visual_review.get("anatomy_leakage_issues"))

    positive_additions: List[str] = []
    negative_additions: List[str] = []
    amendment_reasons: List[str] = []

    if missing:
        names = ", ".join(missing)
        positive_additions.append(
            "CRITICAL: this scene MUST clearly show all of these characters "
            f"together in the same frame: {names}. "
            "Every listed character must be fully visible, no character may "
            "be missing, hidden, or merged into another."
        )
        amendment_reasons.extend(f"missing:{name}" for name in missing)

    for issue in forbidden:
        negative_additions.append(issue)
        amendment_reasons.append(f"forbidden:{issue}")

    for issue in anatomy:
        negative_additions.append(issue)
        amendment_reasons.append(f"anatomy:{issue}")

    if attempt >= 2 and (missing or forbidden or anatomy):
        positive_additions.append(
            "Keep each character's species anatomy strictly separate; "
            "do not blend body parts, fur, shell, ears, or tails between characters."
        )
        amendment_reasons.append("species_anatomy_separation")

    new_prompt = base_prompt
    if positive_additions:
        new_prompt = base_prompt + "\n\n" + "\n".join(positive_additions)

    new_negative = base_negative_prompt
    if negative_additions:
        appended = ", ".join(negative_additions)
        new_negative = (
            f"{base_negative_prompt}, {appended}"
            if base_negative_prompt
            else appended
        )

    return {
        "prompt": new_prompt,
        "negative_prompt": new_negative,
        "amendment_reasons": amendment_reasons,
        "has_amendments": bool(positive_additions or negative_additions),
    }


def summarize_selection_for_history(
    *,
    attempt: int,
    selection: Dict[str, Any],
    amendment_reasons: List[str],
) -> Dict[str, Any]:
    selected = selection.get("selected_asset_ref") or {}
    return {
        "attempt": attempt,
        "best_score": selection.get("best_score"),
        "should_retry": bool(selection.get("should_retry")),
        "selected_file_name": selected.get("file_name"),
        "amendment_reasons": list(amendment_reasons or []),
    }
