from __future__ import annotations

from typing import Any, Dict, List

from app.services.character_visual_profile import build_character_visual_profile


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _join_list(items: Any) -> str:
    if not isinstance(items, list):
        return ""

    return ", ".join(_clean_text(item) for item in items if _clean_text(item))


def clean_image_prompt_text(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    # Remove storyboard helper labels from image prompts.
    # These labels are useful during storyboard construction, but they sound unnatural
    # when passed directly to image generation providers.
    replacements = {
        "主角 ": "",
        "主角": "",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    return text.strip()


def build_visual_profile_prompt_block(profile: Dict[str, Any]) -> str:
    subject = _clean_text(profile.get("subject"))
    source = _clean_text(profile.get("profile_source"))
    identity = _clean_text(profile.get("visual_identity"))
    must_keep = _join_list(profile.get("must_keep"))
    required_presence = _join_list(profile.get("required_presence_rules"))

    if not subject and not identity:
        return ""

    parts = [
        "character visual profile",
        f"profile source: {source}" if source else "",
        f"main subject: {subject}" if subject else "",
        f"fixed visual identity: {identity}" if identity else "",
        f"must keep exactly: {must_keep}" if must_keep else "",
        f"required presence: {required_presence}" if required_presence else "",
        "the main subject is the protagonist of the image, not a background prop",
        "if the story context mentions other characters, keep them secondary and do not replace the main subject",
        "use the same character design in every generated image",
        "do not redesign the main subject between scenes",
        "only change pose, expression, camera angle, background, and current scene action",
    ]

    return "; ".join(part for part in parts if part)


def build_subject_negative_prompt_block(profile: Dict[str, Any]) -> str:
    must_avoid = _join_list(profile.get("must_avoid"))
    if not must_avoid:
        return ""

    return f"subject negative constraints: {must_avoid}"


def build_character_separation_block(outputs: Dict[str, Any]) -> str:
    manifest = outputs.get("character_manifest") or {}
    characters = manifest.get("characters") or []

    if not isinstance(characters, list) or len(characters) < 2:
        return ""

    parts: List[str] = [
        "character separation: keep every character visually distinct",
        "do not transfer visual traits, body parts, clothing, shell, ears, tail, or accessories between characters",
        "each character must keep only its own defined appearance traits",
        "supporting characters may appear, but they must not change the main subject identity",
    ]

    for item in characters:
        if not isinstance(item, dict):
            continue

        name = _clean_text(item.get("display_name"))
        species = _clean_text(item.get("species"))
        traits = item.get("signature_traits") or item.get("visual_traits") or []
        forbidden = item.get("forbidden_traits") or []

        if isinstance(traits, list):
            traits_text = _join_list(traits)
        else:
            traits_text = _clean_text(traits)

        if isinstance(forbidden, list):
            forbidden_text = _join_list(forbidden)
        else:
            forbidden_text = _clean_text(forbidden)

        character_parts = [
            f"{name} ({species})" if name and species else name or species,
            f"must keep only: {traits_text}" if traits_text else "",
            f"must avoid: {forbidden_text}" if forbidden_text else "",
        ]
        character_text = "; ".join(part for part in character_parts if part)
        if character_text:
            parts.append(character_text)

    return "; ".join(parts)


def build_scene_action_binding_block(
    *,
    visual_description: str,
    narration: str,
) -> str:
    visual = clean_image_prompt_text(visual_description)
    story = clean_image_prompt_text(narration)

    parts: List[str] = [
        "scene action binding: depict the exact current scene action, not a generic character portrait",
    ]

    if visual:
        parts.append(f"must show this visual action: {visual}")

    if story:
        parts.append(f"must match this story moment: {story}")

    parts.append(
        "keep the main subject visually consistent while changing only pose, framing, background, and action"
    )
    parts.append(
        "do not let supporting characters or props become the main subject of this image"
    )

    return "; ".join(parts)


def build_image_prompt_policy_blocks(
    *,
    workflow_input: Any,
    outputs: Dict[str, Any],
    visual_description: str,
    narration: str,
    subject_hint: str = "",
) -> Dict[str, Any]:
    profile = build_character_visual_profile(
        workflow_input=workflow_input,
        outputs=outputs,
        subject_hint=subject_hint,
    )

    return {
        "profile": profile,
        "visual_profile_block": build_visual_profile_prompt_block(profile),
        "character_separation_block": build_character_separation_block(outputs),
        "scene_action_block": build_scene_action_binding_block(
            visual_description=visual_description,
            narration=narration,
        ),
        "subject_negative_block": build_subject_negative_prompt_block(profile),
    }
