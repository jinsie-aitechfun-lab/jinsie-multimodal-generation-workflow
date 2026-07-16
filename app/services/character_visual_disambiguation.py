from __future__ import annotations

from typing import Any, Dict


_RED_PANDA_VISUAL_IDENTITY = (
    "A small red panda (Ailurus fulgens), a compact tree-dwelling mammal with "
    "rich reddish-brown fur, a white facial mask, dark tear markings below the "
    "eyes, dark legs, pointed ears, and a long fluffy tail with alternating rings."
)

_RED_PANDA_SIGNATURE_TRAITS = [
    "red panda (Ailurus fulgens), not a giant panda",
    "small compact tree-dwelling animal",
    "rich reddish-brown fur",
    "white facial mask with dark tear markings",
    "dark legs and pointed ears",
    "long fluffy ringed tail",
]

_RED_PANDA_FORBIDDEN_TRAITS = [
    "giant panda",
    "black-and-white panda",
    "giant panda cub",
    "round giant-panda face",
    "large black eye patches",
    "black-and-white bear body",
    "short bear tail",
]


def character_visual_disambiguation(character: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact visual distinction for known ambiguous subject names."""
    if not isinstance(character, dict):
        return {}

    values = [
        str(character.get("display_name") or "").strip(),
        str(character.get("species") or "").strip(),
        str(character.get("subject") or "").strip(),
    ]
    identity = str(character.get("visual_identity") or "").strip()
    is_red_panda = "小熊猫" in values or "red panda" in identity.lower()
    if not is_red_panda:
        return {}

    return {
        "english_species": "red panda",
        "visual_identity": _RED_PANDA_VISUAL_IDENTITY,
        "signature_traits": list(_RED_PANDA_SIGNATURE_TRAITS),
        "forbidden_traits": list(_RED_PANDA_FORBIDDEN_TRAITS),
        "prompt_block": (
            "visual species disambiguation: this character is a red panda "
            "(Ailurus fulgens), a small reddish-brown tree-dwelling mammal with "
            "a white facial mask, dark tear markings, dark legs, pointed ears, "
            "and a long fluffy ringed tail; explicitly not a giant panda, not a "
            "black-and-white panda, not a round-faced giant panda cub, and not a "
            "black-and-white bear"
        ),
    }
