from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


GENERIC_SUBJECTS = {
    "",
    "animal protagonist",
    "protagonist",
    "character",
    "main character",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(items: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()

    for item in items:
        value = _clean_text(item)
        if not value or value in seen:
            continue

        result.append(value)
        seen.add(value)

    return result


def normalize_topic_subject(topic: str) -> str:
    value = _clean_text(topic)

    cleanup_patterns = [
        r"^请写一个关于",
        r"^请讲一个关于",
        r"^请生成一个关于",
        r"^写一个关于",
        r"^讲一个关于",
        r"^生成一个关于",
        r"^关于",
        r"的故事$",
        r"故事$",
    ]

    for pattern in cleanup_patterns:
        value = re.sub(pattern, "", value)

    return value.strip(" ，。,.、")


def extract_conservative_subject(topic: str) -> str:
    """
    Conservative open-subject extraction.

    This function intentionally avoids:
    - animal / object / character collections
    - verb collections
    - species classification

    If the subject is not explicit, keep the cleaned topic phrase instead of
    guessing incorrectly. Later LLM profile generation can refine the subject.
    """
    value = normalize_topic_subject(topic)

    if not value:
        return ""

    return value[:24]


def _known_risk_rules(subject: str) -> Dict[str, List[str]]:
    value = _clean_text(subject)

    # This is not a role/species collection.
    # It only handles a known visual failure mode: tadpoles being rendered as frogs.
    if "蝌蚪" in value:
        return {
            "must_keep": [
                "round head",
                "long thin tail",
                "small aquatic baby body",
                "swimming in water",
                "no legs",
                "no arms",
            ],
            "must_avoid": [
                "frog",
                "adult frog",
                "green frog body",
                "frog legs",
                "four legs",
                "arms",
                "jumping frog",
                "sitting frog",
                "land animal body",
            ],
            "required_presence_rules": [
                "visible tadpole must appear as the main subject in every scene",
                "frog mother may appear only as a secondary character when the story needs it",
                "do not replace tadpole with frog",
                "do not replace the tadpole with an adult frog",
            ],
        }

    if "兔" in value or "rabbit" in value.lower() or "bunny" in value.lower():
        return {
            "must_keep": [
                "small white storybook rabbit",
                "long upright rabbit ears with soft pink inner ears",
                "round fluffy rabbit tail",
                "soft white fur",
                "small red scarf",
            ],
            "must_avoid": [
                "turtle shell",
                "hard round shell",
                "turtle body",
                "short turtle legs",
                "green turtle skin",
                "rabbit replaced by turtle",
            ],
            "required_presence_rules": [
                "the rabbit must be clearly visible as a separate character",
                "do not merge the rabbit with a turtle or shell body",
            ],
        }

    if (
        "乌龟" in value
        or "海龟" in value
        or "龟" in value
        or "turtle" in value.lower()
        or "tortoise" in value.lower()
    ):
        return {
            "must_keep": [
                "small green storybook turtle",
                "round green turtle shell",
                "olive green turtle body",
                "short turtle legs",
                "gentle round eyes",
                "small blue neck scarf",
            ],
            "must_avoid": [
                "rabbit ears",
                "long upright ears",
                "fluffy rabbit tail",
                "rabbit body",
                "white rabbit fur",
                "turtle replaced by rabbit",
            ],
            "required_presence_rules": [
                "the turtle must be clearly visible as a separate character",
                "do not merge the turtle with rabbit ears or rabbit body",
            ],
        }

    return {
        "must_keep": [],
        "must_avoid": [],
        "required_presence_rules": [],
    }


def _generic_visual_identity(subject: str) -> str:
    return (
        f"{subject} is the main storybook character. Give this character one stable, "
        "specific visual design before image generation: fixed body shape, fixed color palette, "
        "fixed facial features, fixed proportions, and one small consistent accessory or detail. "
        "Use exactly the same visual identity in every scene."
    )


def _generic_must_keep(subject: str) -> List[str]:
    return [
        f"same character identity: {subject}",
        "same body shape",
        "same color palette",
        "same facial features",
        "same proportions",
        "same small accessory or signature detail",
        "same storybook illustration style",
    ]


def _generic_must_avoid() -> List[str]:
    return [
        "different main character design",
        "random color changes",
        "random outfit changes",
        "different body shape",
        "different species or object identity",
        "multiple unrelated main subjects",
        "realistic photo style",
    ]


def _existing_visual_profile(outputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    profile = outputs.get("character_visual_profile") or {}
    if isinstance(profile, dict) and profile.get("subject"):
        return dict(profile)

    return None


def _primary_manifest_character(outputs: Dict[str, Any]) -> Dict[str, Any]:
    manifest = outputs.get("character_manifest") or {}
    characters = manifest.get("characters") or []

    if not isinstance(characters, list):
        return {}

    for item in characters:
        if not isinstance(item, dict):
            continue

        if _clean_text(item.get("role_type")) == "primary":
            return item

    return {}


def _extract_subject_from_anchor(anchor: str) -> str:
    value = _clean_text(anchor)
    if not value:
        return ""

    match = re.search(r"main subject:\s*([^,;]+)", value)
    if match:
        return _clean_text(match.group(1))

    return ""


def build_character_visual_profile(
    *,
    workflow_input: Any,
    outputs: Optional[Dict[str, Any]] = None,
    subject_hint: str = "",
) -> Dict[str, Any]:
    outputs = outputs or {}

    existing_profile = _existing_visual_profile(outputs)
    if existing_profile:
        existing_profile.setdefault("profile_source", "existing_profile")
        existing_profile.setdefault("llm_profile_ready", False)
        existing_profile.setdefault("reference_image", None)
        return existing_profile

    topic = _clean_text(getattr(workflow_input, "topic", ""))
    explicit_anchor = _clean_text(
        getattr(workflow_input, "character_consistency_anchor", "")
    )
    hinted_subject = _extract_subject_from_anchor(subject_hint)

    main_character = _clean_text(getattr(workflow_input, "main_character", ""))
    main_display = _clean_text(getattr(workflow_input, "main_character_display", ""))
    main_traits = _clean_text(getattr(workflow_input, "main_character_visual_traits", ""))

    manifest_primary = _primary_manifest_character(outputs)

    subject = ""
    visual_identity = ""
    profile_source = "conservative_fallback"

    if explicit_anchor:
        subject = main_display or main_character or hinted_subject or extract_conservative_subject(topic)
        visual_identity = explicit_anchor
        profile_source = "manual_anchor"
    elif hinted_subject:
        subject = hinted_subject
        visual_identity = _generic_visual_identity(subject)
        profile_source = "subject_hint"
    elif main_display or main_character or main_traits:
        subject = main_display or main_character or extract_conservative_subject(topic)
        visual_identity = main_traits or _generic_visual_identity(subject)
        profile_source = "manual_input"
    elif manifest_primary:
        subject = (
            _clean_text(manifest_primary.get("display_name"))
            or _clean_text(manifest_primary.get("species"))
            or extract_conservative_subject(topic)
        )
        manifest_traits = manifest_primary.get("signature_traits") or manifest_primary.get("visual_traits") or []
        if isinstance(manifest_traits, list):
            manifest_traits_text = ", ".join(
                _clean_text(item) for item in manifest_traits if _clean_text(item)
            )
        else:
            manifest_traits_text = _clean_text(manifest_traits)

        visual_identity = manifest_traits_text or _generic_visual_identity(subject)
        profile_source = "manifest"
    else:
        subject = extract_conservative_subject(topic)
        visual_identity = _generic_visual_identity(subject)
        profile_source = "conservative_fallback"

    if not subject or subject.lower() in GENERIC_SUBJECTS:
        subject = extract_conservative_subject(topic) or "main character"

    risk_rules = _known_risk_rules(subject)

    must_keep = _generic_must_keep(subject)
    must_avoid = _generic_must_avoid()
    required_presence_rules = [
        f"{subject} must be clearly visible in every scene",
        "the main subject must not be replaced by supporting characters, props, or background objects",
    ]

    if main_traits:
        must_keep.insert(0, main_traits)

    if profile_source == "manifest" and "manifest_traits_text" in locals() and manifest_traits_text:
        must_keep.insert(0, manifest_traits_text)

    must_keep.extend(risk_rules["must_keep"])
    must_avoid.extend(risk_rules["must_avoid"])
    required_presence_rules.extend(risk_rules["required_presence_rules"])

    return {
        "subject": subject,
        "profile_source": profile_source,
        "visual_identity": visual_identity,
        "must_keep": _dedupe(must_keep),
        "must_avoid": _dedupe(must_avoid),
        "required_presence_rules": _dedupe(required_presence_rules),
        "reference_image": None,
        "llm_profile_ready": False,
    }


def build_profile_debug_summary(profile: Dict[str, Any]) -> str:
    return (
        f"subject={profile.get('subject')}; "
        f"source={profile.get('profile_source')}; "
        f"llm_ready={profile.get('llm_profile_ready')}"
    )
