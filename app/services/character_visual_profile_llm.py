from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List
from urllib import request as urllib_request

from app.services.character_visual_profile import build_character_visual_profile
from app.services.llm_output_sanitizer import normalize_quotes, strip_code_fences


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


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [_clean_text(item) for item in value if _clean_text(item)]

    if isinstance(value, str):
        text = _clean_text(value)
        if not text:
            return []
        parts = re.split(r"[,，;；\n]+", text)
        return [_clean_text(item) for item in parts if _clean_text(item)]

    return []


def _extract_json_object(content: str) -> Dict[str, Any]:
    raw = normalize_quotes(strip_code_fences(content))
    if not raw:
        return {}

    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if 0 <= start < end:
        snippet = raw[start : end + 1]
        try:
            value = json.loads(snippet)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    return {}


def _story_context(outputs: Dict[str, Any]) -> str:
    story = outputs.get("story") or {}
    text = _clean_text(story.get("text")) or _clean_text(story.get("summary"))
    if not text:
        return ""

    return text[:500]


def _storyboard_context(outputs: Dict[str, Any]) -> str:
    storyboard = outputs.get("storyboard") or {}
    scenes = storyboard.get("scenes") or []
    if not isinstance(scenes, list):
        return ""

    lines: List[str] = []
    for item in scenes[:6]:
        if not isinstance(item, dict):
            continue

        title = _clean_text(item.get("title"))
        visual = _clean_text(item.get("visual_description"))
        narration = _clean_text(item.get("narration"))
        line = " | ".join(part for part in [title, visual, narration] if part)
        if line:
            lines.append(line)

    return "\n".join(lines)[:800]


def _should_skip_llm(base_profile: Dict[str, Any]) -> bool:
    source = _clean_text(base_profile.get("profile_source"))

    # Respect explicit/user/manifest profiles. LLM should enhance weak inferred profiles,
    # not overwrite user-controlled character definitions.
    return source in {
        "manual_anchor",
        "manual_input",
        "manifest",
        "existing_profile",
    }


def _character_profile_provider(runner: Any) -> str:
    configured = os.getenv("CHARACTER_PROFILE_PROVIDER", "").strip()
    if configured:
        return configured

    try:
        return _clean_text(runner._story_provider_name())
    except Exception:
        return ""


def _merge_profile(
    *,
    base_profile: Dict[str, Any],
    llm_payload: Dict[str, Any],
) -> Dict[str, Any]:
    subject = _clean_text(base_profile.get("subject"))
    llm_subject = _clean_text(llm_payload.get("subject"))

    # Never let LLM change the already selected subject in this phase.
    if not subject:
        subject = llm_subject

    visual_identity = _clean_text(llm_payload.get("visual_identity"))
    if not visual_identity:
        visual_identity = _clean_text(base_profile.get("visual_identity"))

    llm_must_keep = _as_list(llm_payload.get("must_keep"))
    llm_must_avoid = _as_list(llm_payload.get("must_avoid"))

    must_keep = _dedupe(_as_list(base_profile.get("must_keep")) + llm_must_keep)
    must_avoid = _dedupe(_as_list(base_profile.get("must_avoid")) + llm_must_avoid)

    required_presence_rules = _as_list(llm_payload.get("required_presence_rules"))
    required_presence_rules = _dedupe(
        [
            f"{subject} must be clearly visible in every scene",
            "the main subject must not be replaced by supporting characters, props, or background objects",
        ]
        + required_presence_rules
    )

    if "蝌蚪" in subject:
        required_presence_rules = _dedupe(
            required_presence_rules
            + [
                "visible tadpole must appear as the main subject",
                "frog mother may appear only as a secondary character when the story needs it",
                "do not replace tadpole with frog",
                "the main subject must be a cute simple tadpole with a round head and long tail",
            ]
        )
        must_keep = _dedupe(
            must_keep
            + [
                "visible tadpole body",
                "round head and long thin tail",
                "no legs and no arms on the tadpole",
            ]
        )
        must_avoid = _dedupe(
            must_avoid
            + [
                "tadpole replaced by frog",
                "adult frog as the only visible subject",
                "frog legs on tadpole",
            ]
        )

    return {
        **base_profile,
        "subject": subject,
        "profile_source": "llm_profile",
        "visual_identity": visual_identity,
        "must_keep": must_keep,
        "must_avoid": must_avoid,
        "required_presence_rules": required_presence_rules,
        "reference_image": base_profile.get("reference_image"),
        "llm_profile_ready": True,
        "llm_confidence": _clean_text(llm_payload.get("confidence")) or "medium",
    }


def build_llm_character_visual_profile(
    runner: Any,
    ctx: Any,
    outputs: Dict[str, Any],
    *,
    subject_hint: str = "",
) -> Dict[str, Any]:
    base_profile = build_character_visual_profile(
        workflow_input=ctx.input,
        outputs=outputs,
        subject_hint=subject_hint,
    )

    if _should_skip_llm(base_profile):
        return base_profile

    provider = _character_profile_provider(runner)
    if provider != "openai_compatible_llm":
        return base_profile

    api_key = _clean_text(runner._llm_api_key())
    model = _clean_text(runner._story_model_name())
    if not api_key or not model:
        return base_profile

    subject = _clean_text(base_profile.get("subject"))
    if not subject:
        return base_profile

    topic = _clean_text(getattr(ctx.input, "topic", ""))
    # Keep story/storyboard context out of the LLM prompt for now.
    # The profile must be a reusable character design sheet, not a scene description.
    # Scene actions are handled later by image_prompt_policy.py.
    system_prompt = (
        "You are a character design director for a children's story-to-video system. "
        "Generate one stable character design sheet profile for image generation. "
        "Return JSON only. Do not use markdown. Do not change the given subject. "
        "The output must describe only the character's reusable appearance. "
        "Do not include temporary scene actions, locations, background objects, other animals, weather, roads, forests, lakes, rivers, meadows, or one-off story events."
    )

    user_prompt = f"""
Create a stable character visual profile for image generation.

Important rules:
- Keep the given subject exactly as provided.
- Do not invent a different main subject.
- Make the visual identity concrete enough for consistent images.
- Choose fixed colors, body shape, facial features, proportions, and one signature detail.
- The visual_identity must describe only the character design sheet.
- Do not include scene locations, backgrounds, temporary actions, nearby animals, weather, roads, lakes, forests, or one-off story events.
- Avoid vague phrases like "fixed color palette" or "consistent appearance" alone.
- Add strict must_avoid rules to prevent common visual drift.
- If the subject is a tadpole, the tadpole must visibly appear; a frog may appear only as a secondary mother character.
- For tadpoles: use a cute simple storybook tadpole design only. Do not mention internal organs, transparent body, anatomy, biological details, frog legs, adult frog body, land animal body, or green frog body.
- If multiple characters appear in the story, do not mix their traits.

Given subject:
{subject}

Topic:
{topic}

Use the topic only to understand what the subject is. Do not copy any imagined plot, location, background, supporting animal, or scene action into the visual profile.

Return JSON with exactly these fields:
{{
  "subject": "{subject}",
  "visual_identity": "one concrete English character design phrase, 35-80 words, no scene/background/action",
  "must_keep": ["fixed color trait", "fixed body shape trait", "fixed face trait", "fixed signature detail"],
  "must_avoid": ["visual drift risk 1", "wrong subject risk 2", "scene-specific contamination risk 3"],
  "required_presence_rules": ["the given subject must be clearly visible", "the subject must not be replaced by another character"],
  "confidence": "high|medium|low"
}}
""".strip()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 700,
    }

    req = urllib_request.Request(
        runner._llm_api_base_url().rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=runner._story_timeout_seconds()) as resp:
            raw = resp.read()
    except Exception:
        return base_profile

    if not raw:
        return base_profile

    try:
        data = json.loads(raw.decode("utf-8", errors="ignore"))
    except Exception:
        return base_profile

    content = (
        (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
        or ""
    ).strip()

    llm_payload = _extract_json_object(content)
    if not llm_payload:
        return base_profile

    visual_identity = _clean_text(llm_payload.get("visual_identity"))
    must_keep = _as_list(llm_payload.get("must_keep"))

    scene_specific_terms = [
        "forest path",
        "forest",
        "lake",
        "nearby",
        "background",
        "driving on",
        "flying over",
        "meadow",
        "wildflowers",
        "trees in the background",
        "struggling bird",
        "bird nearby",
        "road",
        "river",
        "weather",
        "sunset",
        "morning light",
        "in the story",
        "internal organs",
        "transparent body",
        "slightly transparent",
    ]
    lower_identity = visual_identity.lower()

    if any(term in lower_identity for term in scene_specific_terms):
        return base_profile

    if len(visual_identity) < 40 or len(must_keep) < 3:
        return base_profile

    return _merge_profile(
        base_profile=base_profile,
        llm_payload=llm_payload,
    )
