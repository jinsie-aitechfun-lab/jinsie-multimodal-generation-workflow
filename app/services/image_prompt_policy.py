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


def build_known_failure_mode_block(profile: Dict[str, Any]) -> str:
    subject = _clean_text(profile.get("subject"))
    must_keep_text = _join_list(profile.get("must_keep"))
    must_avoid_text = _join_list(profile.get("must_avoid"))
    required_presence_text = _join_list(profile.get("required_presence_rules"))

    if "蝌蚪" not in subject and "tadpole" not in subject.lower():
        return ""

    parts = [
        "known failure mode reinforcement",
        "the main subject is a tadpole, not a frog",
        "must show a visible tadpole as the main subject in every scene",
        "must show a round tadpole head, a long thin tail, and a small aquatic baby body",
        "the tadpole must not be replaced by an adult frog",
        "no four legs, no frog legs, no arms, no adult frog body",
        "if a mother frog appears, she must be a supporting character only",
        "the tadpole must remain clearly visible as the main subject even when other characters appear",
        f"tadpole must keep: {must_keep_text}" if must_keep_text else "",
        f"tadpole must avoid: {must_avoid_text}" if must_avoid_text else "",
        f"tadpole required presence: {required_presence_text}" if required_presence_text else "",
    ]

    return "; ".join(part for part in parts if part)


def build_visual_profile_prompt_block(profile: Dict[str, Any]) -> str:
    subject = _clean_text(profile.get("subject"))
    source = _clean_text(profile.get("profile_source"))
    identity = _clean_text(profile.get("visual_identity"))
    must_keep = _join_list(profile.get("must_keep"))
    required_presence = _join_list(profile.get("required_presence_rules"))
    known_failure_mode = build_known_failure_mode_block(profile)

    if not subject and not identity:
        return ""

    parts = [
        "character visual profile",
        f"profile source: {source}" if source else "",
        f"main subject: {subject}" if subject else "",
        f"fixed visual identity: {identity}" if identity else "",
        f"must keep exactly: {must_keep}" if must_keep else "",
        f"required presence: {required_presence}" if required_presence else "",
        known_failure_mode,
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


def build_multi_character_visual_profiles_block(outputs: Dict[str, Any]) -> str:
    payload = outputs.get("character_visual_profiles") or {}
    profiles = payload.get("profiles") or []

    if not isinstance(profiles, list) or len(profiles) < 2:
        return ""

    parts: List[str] = [
        "multi-character identity lock",
        "render all required scene characters together in the same frame",
        "treat every character as a separate visual identity with exclusive ownership of its defining traits",
        "never merge anatomies, never swap signature traits, and never transfer body parts, shells, ears, tails, fur patterns, skin patterns, or accessories between characters",
        "a defining trait that belongs to one character must not appear on any other character in the same image",
    ]

    character_labels: List[str] = []

    for index, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            continue

        name = _clean_text(profile.get("display_name")) or _clean_text(profile.get("subject")) or f"character_{index}"
        role_type = _clean_text(profile.get("role_type"))
        species = _clean_text(profile.get("species"))
        identity = _clean_text(profile.get("visual_identity"))
        must_keep = _join_list(profile.get("must_keep"))
        must_avoid = _join_list(profile.get("must_avoid"))

        character_labels.append(name)

        character_parts = [
            f"character {index}",
            f"name: {name}",
            f"role: {role_type}" if role_type else "",
            f"species: {species}" if species else "",
            f"fixed visual identity: {identity}" if identity else "",
            f"this character owns only these defining traits: {must_keep}" if must_keep else "",
            f"this character must never have these foreign traits: {must_avoid}" if must_avoid else "",
        ]
        character_text = "; ".join(part for part in character_parts if part)
        if character_text:
            parts.append(character_text)

    if len(character_labels) >= 2:
        parts.append(
            "cross-character exclusion rule: keep every character visually distinct; do not let one character inherit another character's defining anatomy or signature details"
        )

    parts.append(
        "consistency rule: keep the same character design for every character across all scenes; only change pose, expression, framing, background, and current scene action"
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
        "character_visual_profiles_block": build_multi_character_visual_profiles_block(outputs),
        "character_separation_block": build_character_separation_block(outputs),
        "scene_action_block": build_scene_action_binding_block(
            visual_description=visual_description,
            narration=narration,
        ),
        "subject_negative_block": build_subject_negative_prompt_block(profile),
    }
