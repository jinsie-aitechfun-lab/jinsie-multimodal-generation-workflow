from __future__ import annotations

from typing import Any, Dict, Optional


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

    lower = t.lower()

    # --- cat ---
    if ("猫" in t) or ("cat" in lower) or ("kitten" in lower):
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
    if ("狗" in t) or ("dog" in lower) or ("puppy" in lower):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小狗",
            "species": "dog",
            "visual_traits": "cute puppy, round friendly face, dog-like paws, dog tail, moderate ears",
            "forbidden_traits": "fox snout, raccoon mask, mouse face, rabbit ears, turtle shell",
        }

    # --- rabbit ---
    if ("兔" in t) or ("rabbit" in lower) or ("bunny" in lower):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小兔子",
            "species": "rabbit",
            "visual_traits": "cute bunny, long rabbit ears, round face, fluffy fur",
            "forbidden_traits": "cat ears, fox snout, turtle shell, raccoon mask, mouse face",
        }

    # --- turtle ---
    if ("乌龟" in t) or ("龟" in t) or ("turtle" in lower):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小乌龟",
            "species": "turtle",
            "visual_traits": "cute small turtle, clear round shell, short legs, turtle face",
            "forbidden_traits": "rabbit ears, cat ears, fox snout, raccoon mask, mouse face",
        }

    # --- seal ---
    if ("海豹" in t) or ("seal" in lower):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小海豹",
            "species": "seal",
            "visual_traits": "cute baby seal, round face, big eyes, smooth gray fur, short flippers",
            "forbidden_traits": "fox snout, raccoon mask, mouse face, rabbit ears, turtle shell",
        }

    # --- robot ---
    if ("机器人" in t) or ("robot" in lower):
        return {
            "id": "primary-1",
            "role_type": "primary",
            "display_name": "小机器人",
            "species": "robot",
            "visual_traits": "cute small robot, rounded body, friendly screen face, simple limbs, clean design",
            "forbidden_traits": "animal ears, fur, whiskers, snout",
        }

    return None
