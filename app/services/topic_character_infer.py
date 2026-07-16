from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.services.story_subject_extractor import extract_story_subjects


def _normalized_primary_subject(topic: str) -> str:
    extracted = extract_story_subjects(topic)
    subject = str(extracted.primary_subject or "").strip().lower()
    if subject.startswith("小") and len(subject) > 1:
        subject = subject[1:]
    return subject


def _matches_subject(
    *,
    subject: str,
    topic: str,
    chinese_names: tuple[str, ...],
    english_names: tuple[str, ...],
) -> bool:
    if subject in chinese_names:
        return True

    lower = str(topic or "").lower()
    return any(
        re.search(rf"\b{re.escape(name)}\b", lower)
        for name in english_names
    )


def infer_primary_character_manifest(topic: str) -> Optional[Dict[str, Any]]:
    """
    Infer a minimal primary character manifest from topic text.

    Returns a dict compatible with runner's character_manifest items:
      {
        "id": "primary-1",
        "role_type": "primary",
        "display_name": "小猫",
        "species": "cat",
        "visual_traits": "...",
        "forbidden_traits": "..."
      }
    """
    t = (topic or "").strip()
    if not t:
        return None

    primary_subject = _normalized_primary_subject(t)

    # --- cat ---
    if _matches_subject(
        subject=primary_subject,
        topic=t,
        chinese_names=("猫",),
        english_names=("cat", "kitten"),
    ):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小猫",
            "species": "cat",
            "visual_traits": (
                "domestic kitten, round cat face, short muzzle, moderate-sized triangular ears, "
                "visible whiskers, cat-like paws, long cat tail"
            ),
            "forbidden_traits": (
                "fox snout, fennec fox ears, raccoon mask, mouse face, rabbit ears, turtle shell"
            ),
        }

    # --- dog ---
    if _matches_subject(
        subject=primary_subject,
        topic=t,
        chinese_names=("狗",),
        english_names=("dog", "puppy"),
    ):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小狗",
            "species": "dog",
            "visual_traits": "cute puppy, round friendly face, dog-like paws, dog tail, moderate ears",
            "forbidden_traits": "fox snout, raccoon mask, mouse face, rabbit ears, turtle shell",
        }

    # --- rabbit ---
    if _matches_subject(
        subject=primary_subject,
        topic=t,
        chinese_names=("兔", "兔子"),
        english_names=("rabbit", "bunny"),
    ):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小兔子",
            "species": "rabbit",
            "visual_traits": "cute bunny, long rabbit ears, round face, fluffy fur",
            "forbidden_traits": "cat ears, fox snout, turtle shell, raccoon mask, mouse face",
        }

    # --- turtle ---
    if _matches_subject(
        subject=primary_subject,
        topic=t,
        chinese_names=("乌龟", "龟"),
        english_names=("turtle", "tortoise"),
    ):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小乌龟",
            "species": "turtle",
            "visual_traits": "cute small turtle, clear round shell, short legs, turtle face",
            "forbidden_traits": "rabbit ears, cat ears, fox snout, raccoon mask, mouse face",
        }

    # --- seal ---
    if _matches_subject(
        subject=primary_subject,
        topic=t,
        chinese_names=("海豹",),
        english_names=("seal",),
    ):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小海豹",
            "species": "seal",
            "visual_traits": "cute baby seal, round face, big eyes, smooth gray fur, short flippers",
            "forbidden_traits": "fox snout, raccoon mask, mouse face, rabbit ears, turtle shell",
        }

    # --- robot ---
    if _matches_subject(
        subject=primary_subject,
        topic=t,
        chinese_names=("机器人",),
        english_names=("robot",),
    ):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小机器人",
            "species": "robot",
            "visual_traits": "cute small robot, rounded body, friendly screen face, simple limbs, clean design",
            "forbidden_traits": "animal ears, fur, whiskers, snout",
        }

    return None
