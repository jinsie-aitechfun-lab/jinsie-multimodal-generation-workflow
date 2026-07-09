from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.character_visual_profile_llm import (
    build_llm_character_visual_profile,
    build_llm_character_visual_profiles,
)
from app.services.image_prompt_policy import (
    build_image_prompt_policy_blocks,
    clean_image_prompt_text,
)
from app.services.storage_ids import safe_child_dir

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _scene_position_anchor(
    scene_index: int,
    total: int,
    scene: Dict[str, Any],
    narration_text: str,
) -> str:
    """Strong scene-unique anchor placed early in the prompt.

    Diffusion models weight the beginning of the prompt most heavily. By
    inserting the current scene's position + title + a slice of the actual
    narration BEFORE the long character-identity lock blocks, the model
    is forced to encode this scene's unique story moment instead of
    settling on "a generic character portrait" shared with other scenes.
    The clean_image_prompt_text() pass strips any "主角" labels that would
    otherwise leak into the rendered image as Chinese characters.
    """
    pos = scene_index + 1
    title = str(scene.get("scene_title") or "").strip()
    moment = clean_image_prompt_text(narration_text)[:160] if narration_text else ""
    parts: List[str] = [f"scene {pos} of {total}"]
    if title:
        parts.append(f"scene title: {title}")
    if moment:
        parts.append(f"current story moment: {moment}")
    parts.append(
        "this is a unique moment of the story, not a generic character portrait"
    )
    return ", ".join(parts)


def _anti_repeat_block(scene_index: int, total: int) -> str:
    """Anti-repetition tail block — explicitly demand visual variation
    across scenes. Without this, when every scene's prompt shares the
    same long character lock, the diffusion model tends to converge on
    a single canonical pose for every scene."""
    pos = scene_index + 1
    return (
        f"this is scene {pos} of {total}; "
        "the composition, camera angle, environment, mood, and visible action "
        "must visibly differ from the other scenes of this story; "
        "do not reuse the composition, lighting, or background from any other scene"
    )


def _scene_action_fallback(
    visual_description: str,
    narration: str,
    scene_title: str,
) -> str:
    """Build a scene-specific "visual focus" string for the image prompt.

    Combines narration (which is per-scene unique because the story-text
    splitter gives each scene its own paragraph) with the LLM-enriched
    visual_description (which can be missing or recycled across cycled
    scenes when LLM enrichment partially fails). Putting narration FIRST
    guarantees each scene's prompt carries its own plot beat in the
    high-weight region of the prompt, even if visual_description fell
    back to a blueprint duplicate.
    """
    narration_clean = clean_image_prompt_text(narration)[:160] if narration else ""
    visual = clean_image_prompt_text(visual_description) if visual_description else ""
    if narration_clean and visual:
        return f"{narration_clean}; {visual}"
    if narration_clean:
        return narration_clean
    if visual:
        return visual[:200]
    title = clean_image_prompt_text(scene_title)
    if title:
        return f"the scene depicting {title}"
    return ""


def _english_label_for_character(character: Dict[str, Any]) -> str:
    """Return a short English species noun for the diffusion prompt.

    The auto-manifest copies the Chinese topic subject straight into the
    `species` and `display_name` fields (e.g. species="小兔子" for a
    Chinese topic "小兔子和小松鼠"). Diffusion providers like Kolors don't
    reliably parse Chinese animal names mixed into an otherwise-English
    prompt — they ignore the Chinese tokens and latch onto whatever
    English animal word appears in the storyboard's visual_description,
    so both required characters end up rendered as the LLM-mentioned
    species (e.g. two squirrels).

    This returns a SHORT noun ("rabbit", "squirrel") rather than the
    whole descriptive phrase, so the downstream `not two <species>`
    negatives stay clean and high-signal. Resolution chain — no
    hardcoded animal table:

      1. `species` if ASCII-only — already English
      2. Trailing noun of the first clause of `visual_identity`
         (LLM-generated English text), split on common connectors
         like " with ", " who ", " that " — e.g. from
         "white long-eared rabbit with pink twitching nose..." we
         keep "white long-eared rabbit" then take the last word
         "rabbit".
      3. `display_name` if ASCII-only
      4. `subject` if ASCII-only
      5. Original Chinese species / display as a last resort so the
         prompt isn't empty.
    """
    if not isinstance(character, dict):
        return ""

    def _ascii_only(s: str) -> bool:
        return bool(s) and all(ord(c) < 128 for c in s)

    species = str(character.get("species") or "").strip()
    if _ascii_only(species):
        return species

    identity = str(character.get("visual_identity") or "").strip()
    if identity:
        # First sentence only — descriptions like "rabbit. The rabbit wears..."
        # have all the info we need in the first clause.
        first = identity.split(".")[0].strip()
        # IMPORTANT: check for connectors BEFORE splitting on commas.
        # Real visual_identity strings often start with stacked adjectives
        # separated by commas before the species noun, e.g.
        #   "A small, fluffy white rabbit with big eyes..."
        # Splitting on the first comma here gives "A small" → last token
        # "small" — wrong. Splitting on " with " first gives
        # "A small, fluffy white rabbit" → last token "rabbit" — correct.
        for connector in (
            " with ",
            " who ",
            " that ",
            " having ",
            " wearing ",
            " carrying ",
        ):
            if connector in first:
                first = first.split(connector, 1)[0].strip()
                break
        else:
            # Connector not found — fall back to first comma so we
            # don't accidentally grab descriptors from later clauses.
            first = first.split(",")[0].strip()
        if first and any(ord(c) < 128 for c in first):
            cleaned = "".join(c if ord(c) < 128 else " " for c in first).strip()
            cleaned = " ".join(cleaned.split())
            if cleaned:
                # Skip leading articles before grabbing the head noun.
                tokens = [t for t in cleaned.split() if t.lower() not in {"a", "an", "the"}]
                # Strip trailing punctuation that may have stuck to the
                # token (e.g. "rabbit," → "rabbit").
                if tokens:
                    last = tokens[-1].lower().strip(",;:.!?")
                    if last:
                        return last

    display = str(character.get("display_name") or "").strip()
    if _ascii_only(display):
        return display

    subject = str(character.get("subject") or "").strip()
    if _ascii_only(subject):
        return subject

    return species or display or subject or ""


_VOWELS = set("aeiou")


def _pluralize(word: str) -> str:
    """Tiny English pluralizer for species nouns. Not perfect — falls back
    to suffix '+s' for unknown shapes — but covers rabbit/rabbits,
    squirrel/squirrels, mouse/mice, fox/foxes, etc.

    No hardcoded animal list: this only knows English suffix rules.
    """
    w = (word or "").strip().lower()
    if not w:
        return ""
    # Common irregulars worth handling so the prompt reads naturally.
    irregulars = {
        "mouse": "mice",
        "goose": "geese",
        "child": "children",
        "person": "people",
        "tooth": "teeth",
        "foot": "feet",
    }
    if w in irregulars:
        return irregulars[w]
    # Words ending in s, x, z, ch, sh → +es. Otherwise +s.
    if w.endswith(("s", "x", "z")) or w.endswith(("ch", "sh")):
        return w + "es"
    # Word ending in consonant + y → -ies.
    if w.endswith("y") and len(w) > 1 and w[-2].lower() not in _VOWELS:
        return w[:-1] + "ies"
    return w + "s"


def species_count_map(
    enriched_scene_characters: List[Dict[str, Any]],
) -> "Counter[str]":
    """Group required scene characters by their extracted English species
    label and return a Counter of {species: count}.

    This is the foundation for honoring same-species scenes ("rabbit and
    rabbit mom" = {"rabbit": 2}) without falsely flagging them as
    duplicates. All downstream multi-character prompt builders should
    derive count language from this.

    Characters with no extractable English label are skipped here — they
    fall back to the existing Chinese-name path elsewhere in the prompt.
    """
    counts: "Counter[str]" = Counter()
    if not enriched_scene_characters:
        return counts
    for character in enriched_scene_characters:
        if not isinstance(character, dict):
            continue
        label = _english_label_for_character(character)
        if not label:
            continue
        counts[label] += 1
    return counts


def _format_species_count_phrase(counts: "Counter[str]") -> str:
    """Format a Counter into prompt-friendly text:
      {"rabbit": 1, "squirrel": 1} → "1 rabbit and 1 squirrel"
      {"rabbit": 2}                → "2 rabbits"
      {"rabbit": 2, "squirrel": 1} → "2 rabbits and 1 squirrel"
    """
    if not counts:
        return ""
    parts: List[str] = []
    for species, n in counts.items():
        word = species if n == 1 else _pluralize(species)
        parts.append(f"{n} {word}")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


# A small, finite set of common animal body-part words. This is NOT a
# species list — it's the anatomy vocabulary that applies to all
# animals. Adding new body parts here is safe; it never enumerates
# species.
_BODY_PART_WORDS = (
    "ears", "ear",
    "tail", "tails",
    "shell", "shells",
    "horns", "horn", "antlers", "antler",
    "beak", "beaks", "snout", "snouts",
    "wings", "wing",
    "fur", "fleece", "wool",
    "scales", "scale",
    "skin",
    "paws", "paw", "hooves", "hoof", "claws", "claw",
    "mane", "manes",
    "whiskers", "whisker",
    "fangs", "fang", "tusks", "tusk",
    "fins", "fin", "flippers", "flipper",
    "trunk", "trunks",
)


def _distinctive_anatomy_phrases(character: Dict[str, Any]) -> List[str]:
    """Extract short "<adjective(s)> <body-part>" phrases from a
    character's must_keep / visual_identity / signature_traits. These
    become the cross-species anatomy rules — "only X may have <phrase>".

    Heuristic-only — no species enumeration. We just scan for the
    finite anatomy vocabulary above and grab a couple of leading
    adjectives.
    """
    if not isinstance(character, dict):
        return []
    sources: List[str] = []
    for key in ("must_keep", "signature_traits"):
        value = character.get(key) or []
        if isinstance(value, list):
            sources.extend(str(v or "").strip() for v in value if v)
        else:
            sources.append(str(value or "").strip())
    identity = str(character.get("visual_identity") or "").strip()
    if identity:
        # First clause only — descriptions like "rabbit. The rabbit
        # wears..." don't add anatomy info in later sentences.
        sources.append(identity.split(".")[0])

    body_set = set(_BODY_PART_WORDS)
    seen: set = set()
    phrases: List[str] = []
    for src in sources:
        text = " ".join(src.lower().replace(",", " ").replace(";", " ").split())
        tokens = text.split()
        for i, token in enumerate(tokens):
            if token not in body_set:
                continue
            # Walk back up to 3 adjectives until we hit a stopword.
            start = i
            stopwords = {
                "a", "an", "the", "and", "with", "of", "that", "who",
                "having", "wearing", "or", "also", "but", "to", "in",
                "around", "on", "for", "by", "must", "should",
                "same", "small", "tiny", "big", "large",
            }
            for j in range(1, 4):
                if start - 1 < 0:
                    break
                prev = tokens[start - 1].strip(",.")
                if not prev or prev in stopwords:
                    break
                if prev in body_set:
                    break
                start -= 1
            phrase = " ".join(tokens[start : i + 1]).strip(",. ")
            # Need at least one adjective for the rule to be useful —
            # bare "tail" / "ears" alone is too generic to enforce.
            if start == i:
                continue
            if phrase and phrase not in seen:
                seen.add(phrase)
                phrases.append(phrase)
    return phrases


def build_anatomy_separation_rules(
    enriched_scene_characters: List[Dict[str, Any]],
) -> str:
    """Derive anatomy-separation rules from each character's profile.

    For a rabbit-and-squirrel cast, produces something like:
      "only the rabbit may have long upright ears, round fluffy tail;
       only the squirrel may have brown fur, bushy tail;
       do not transfer body parts between species"

    For a same-species cast (rabbit + rabbit mom) returns empty string —
    there's no cross-species body-part conflict to guard against.

    No hardcoded species list. The anatomy vocabulary itself
    (ears/tail/shell/...) is finite and applies to all animals.
    """
    if not isinstance(enriched_scene_characters, list) or len(enriched_scene_characters) < 2:
        return ""

    counts = species_count_map(enriched_scene_characters)
    if len(counts) < 2:
        # Same-species cast — no cross-species anatomy rules needed.
        return ""

    # Group anatomy phrases by extracted English species.
    by_species: Dict[str, List[str]] = {}
    for char in enriched_scene_characters:
        if not isinstance(char, dict):
            continue
        species = _english_label_for_character(char)
        if not species:
            continue
        phrases = _distinctive_anatomy_phrases(char)
        if not phrases:
            continue
        bucket = by_species.setdefault(species, [])
        for p in phrases:
            if p not in bucket:
                bucket.append(p)

    if not by_species:
        return ""

    parts: List[str] = []
    for species, phrases in by_species.items():
        if not phrases:
            continue
        joined = ", ".join(phrases[:4])  # cap to keep prompt readable
        parts.append(f"only the {species} may have {joined}")
    if not parts:
        return ""
    parts.append("do not transfer body parts between different species")
    return "; ".join(parts)


def build_multi_character_negative_prompt(
    enriched_scene_characters: List[Dict[str, Any]],
) -> str:
    """Build a negative prompt aimed at the most common multi-character
    failure modes from diffusion models (Kolors and similar):

    - Both characters rendered as the same species (e.g. two squirrels
      instead of one rabbit + one squirrel)
    - Mirrored / duplicated subjects
    - One character missing entirely (solo portrait)

    Returns empty string for single-character scenes so we don't dilute
    the negative prompt for cases where this isn't a risk.
    """
    if not enriched_scene_characters or len(enriched_scene_characters) < 2:
        return ""

    counts = species_count_map(enriched_scene_characters)
    if not counts:
        return ""

    # Universal negatives — always safe regardless of cast composition.
    parts: List[str] = [
        "duplicate characters beyond required count",
        "missing one required character",
        "only one character visible when multiple are required",
    ]

    # Mirror / identical-rendering negatives only when the cast contains
    # multiple distinct species. For same-species casts (e.g. rabbit +
    # rabbit mom) the model legitimately needs to render two of the same
    # species, so we must not forbid mirroring or "same animal twice"
    # phrasing — it would suppress correct output.
    if len(counts) >= 2:
        parts.extend(
            [
                "two different species merged into one body",
                "characters swapped between species",
            ]
        )

    # Per-species count guard: forbid counts ABOVE the expected count.
    # For required=1 squirrel → forbid "two squirrels, three squirrels".
    # For required=2 rabbits → forbid "three rabbits, four rabbits" but
    # leave "two rabbits" untouched (that's the correct count).
    count_words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
    for species, required in counts.items():
        plural = _pluralize(species)
        # Always forbid 1 more than required, plus a couple steps beyond.
        for over in range(required + 1, required + 4):
            word = count_words.get(over, str(over))
            parts.append(f"{word} {plural}")
        parts.append(f"more than {required} {plural if required > 1 else species}")

    return ", ".join(parts)


def ensure_multi_character_anchor(
    prompt: str,
    enriched_scene_characters: List[Dict[str, Any]],
) -> str:
    """Last-mile guard for any prompt that's about to hit the image
    provider. If the scene has 2+ required characters and the prompt
    text doesn't already contain the multi-character roster / anti-
    mirror negatives, prepend the roster block.

    Why this exists separately from the assembly-time injection: there
    are several fallback paths that build a base_prompt directly from
    `scene.visual_description` / `scene.narration` / a placeholder
    string when `outputs["image_prompts"]` is empty or missing the
    scene_id — runner_single_scene_image_support (API + pillow
    branches), image_provider_queue (shot + scene branches). Without
    a defense at this layer, a single missing image_prompts entry can
    silently send a bare single-species prompt to the provider.
    """
    text = str(prompt or "")
    if not isinstance(enriched_scene_characters, list) or len(enriched_scene_characters) < 2:
        return text
    lowered = text.lower()
    if "not two " in lowered or "do not draw mirrored" in lowered:
        return text
    roster = _build_multi_character_roster_for_scene(enriched_scene_characters)
    if not roster:
        return text
    return f"{roster}, {text}" if text else roster


def _build_multi_character_roster_for_scene(
    enriched_scene_characters: List[Dict[str, Any]],
) -> str:
    """Reinforcement block injected next to per-scene text fields when a
    scene has 2+ required characters.

    Why this exists: the multi-character color_prefix at PROMPT POSITION 0
    declares "rabbit and squirrel". But the storyboard's per-scene
    `visual_description` may name only ONE species (e.g. "the squirrel
    jumps from rock to rock") because the storyboard LLM only sees the
    narration and isn't forced to mention every character. Diffusion
    models give heavy weight to the explicitly-named species in the
    scene text and end up rendering BOTH characters as that species
    (mirrored squirrels). The roster injected here re-asserts every
    required species adjacent to the scene-specific text, so the
    explicit single-species mention can't dominate.
    """
    if not isinstance(enriched_scene_characters, list) or len(enriched_scene_characters) < 2:
        return ""

    counts = species_count_map(enriched_scene_characters)
    if not counts:
        return ""

    total = sum(counts.values())
    species_set: List[str] = list(counts.keys())
    count_phrase = _format_species_count_phrase(counts)  # "2 rabbits and 1 squirrel"

    parts: List[str] = [
        f"this scene contains exactly {count_phrase}",
        f"render exactly {total} distinct animal subjects in total",
        f"required species in this single image: {', '.join(species_set)}",
    ]

    # Per-species count guards. For required=1 squirrel → "not two squirrels".
    # For required=2 rabbits → "not three rabbits" but NEVER "not two
    # rabbits" — that would block the legitimate output for same-species
    # casts (rabbit + rabbit mom).
    count_words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
    for species, required in counts.items():
        plural = _pluralize(species)
        over = required + 1
        word = count_words.get(over, str(over))
        parts.append(f"not {word} {plural} in this image")
        parts.append(f"do not render more than {required} {plural if required > 1 else species}")

    # Cross-species "do not swap" rules only when there are 2+ distinct
    # species in the cast. For same-species cast (all rabbits) there's
    # nothing to swap with, so we skip these to avoid noise.
    if len(species_set) >= 2:
        for s in species_set:
            parts.append(f"do not turn any other character into a {s}")
        parts.append("do not duplicate a single character; do not mirror one character to fake another")

    return ", ".join(parts)


def _scene_text_mentions_all_species(
    text: str,
    enriched_scene_characters: List[Dict[str, Any]],
) -> bool:
    """Returns True if every required character's species (or display name)
    appears in the given text. Used to decide whether the per-scene
    visual_description / narration is already self-sufficient or whether
    we need to surface the roster reinforcement block."""
    if not text:
        return False
    if not isinstance(enriched_scene_characters, list) or len(enriched_scene_characters) < 2:
        return True
    lowered = text.lower()
    for character in enriched_scene_characters:
        if not isinstance(character, dict):
            continue
        species = str(character.get("species") or "").strip().lower()
        display = str(character.get("display_name") or "").strip().lower()
        candidates = [c for c in [species, display] if c]
        if not candidates:
            continue
        if not any(c in lowered or c in text for c in candidates):
            return False
    return True


def _write_image_prompts_debug(workflow_id: str, prompts: List[Dict[str, Any]]) -> None:
    """Write a per-run debug file with every scene's final prompt so the
    output can be inspected after generation. Failures here are non-fatal
    — debug logging must never break the actual image generation."""
    wf = str(workflow_id or "").strip()
    if not wf:
        return
    try:
        out_dir = safe_child_dir(
            PROJECT_ROOT / "assets" / "mock",
            wf,
            field_name="workflow_id",
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        debug_path = out_dir / "image_prompts_debug.json"
        debug_payload = {
            "workflow_id": wf,
            "scene_count": len(prompts),
            "prompts": [
                {
                    "scene_id": str(p.get("scene_id") or "").strip(),
                    "scene_title": str(p.get("scene_title") or "").strip(),
                    "required_character_names": p.get("required_character_names") or [],
                    "prompt": str(p.get("prompt") or ""),
                    "prompt_char_count": len(str(p.get("prompt") or "")),
                }
                for p in prompts
            ],
        }
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(debug_payload, f, ensure_ascii=False, indent=2)
        print(
            f"[RunnerImagePromptsSupport] wrote per-scene image prompts debug → {debug_path}"
        )
    except Exception as error:  # noqa: BLE001
        print(f"[RunnerImagePromptsSupport] image prompts debug write failed: {error}")


class RunnerImagePromptsSupport:
    """Image prompt assembly extracted from WorkflowRunner.

    Extracted as Step 11 of the runner refactor. This module owns the
    image-prompt output assembly and character anchor metadata while delegating
    shared character and scene helpers back to WorkflowRunner.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def run_image_prompts(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        runner = self._runner
        sentence_shots = outputs.get("sentence_shots") or {}
        shot_items = sentence_shots.get("items") or []

        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        image_size = __import__("os").getenv(
            "SILICONFLOW_IMAGE_SIZE", "1280x720"
        ).strip()
        framing = "vertical 9:16 framing" if image_size.startswith("720") else "horizontal 16:9 framing"
        global_style_anchor = (
            f"{ctx.input.visual_style} illustration, "
            f"{ctx.input.tone} mood, "
            "children's storybook art, "
            "soft pastel palette, "
            "clean composition, "
            "consistent character design, "
            f"{framing}"
        )

        character_anchor = runner._character_consistency_anchor(ctx, outputs)

        prompts: List[Dict[str, Any]] = []
        character_visual_profile: Dict[str, Any] = build_llm_character_visual_profile(
            runner,
            ctx,
            outputs,
            subject_hint=character_anchor,
        )
        character_visual_profiles: Dict[str, Any] = build_llm_character_visual_profiles(
            runner,
            ctx,
            outputs,
        )

        enriched_character_manifest = runner._character_manifest_support.apply_visual_profiles_to_character_manifest(
            outputs.get("character_manifest") or {},
            character_visual_profiles,
        )
        if enriched_character_manifest:
            outputs["character_manifest"] = enriched_character_manifest

        character_anchor_metadata: Dict[str, Any] = {
            "enabled": True,
            "mode": "text_profile_anchor",
            "anchor_type": "character_reference_anchor",
            "subject": character_visual_profile.get("subject"),
            "profile_source": character_visual_profile.get("profile_source"),
            "profile_generation_source": character_visual_profile.get(
                "profile_generation_source"
            ),
            "visual_identity": character_visual_profile.get("visual_identity"),
            "reference_images": [],
            "reference_image": None,
            "provider_reference_support": {
                "requested": True,
                "provider_supports_reference_image": False,
                "mode": "metadata_only",
                "reason": (
                    "current api_image_generator text-to-image adapter does not "
                    "send reference images yet"
                ),
            },
        }

        profile_outputs: Dict[str, Any] = {
            **outputs,
            "character_visual_profile": character_visual_profile,
            "character_visual_profiles": character_visual_profiles,
            "character_anchor": character_anchor_metadata,
        }

        if shot_items:
            scene_map: Dict[str, Dict[str, Any]] = {
                str(scene.get("scene_id") or "").strip(): scene
                for scene in scenes
                if isinstance(scene, dict)
            }
            total_shots = len(shot_items)

            for shot_index, shot in enumerate(shot_items):
                shot_id = str(shot.get("shot_id") or "").strip()
                scene_id = str(shot.get("scene_id") or "").strip()
                scene_title = str(shot.get("scene_title") or "").strip()
                visual_description = str(shot.get("visual_description") or "").strip()
                shot_type = str(shot.get("shot_type") or "medium").strip()
                transition = str(shot.get("transition") or "fade").strip()
                text = str(shot.get("text") or "").strip()

                scene_data = scene_map.get(scene_id) or {}

                # Robust scene-specific focus: when visual_description is
                # empty (LLM enrichment failed), synthesize from narration
                # or scene_title so the scene anchor isn't reduced to a
                # blank "visual focus: " that's identical across scenes.
                scene_focus = _scene_action_fallback(
                    visual_description=visual_description,
                    narration=text,
                    scene_title=scene_title,
                )
                enriched_scene_characters = (
                    runner._scene_characters.enriched_scene_characters_from_manifest(
                        outputs,
                        scene_data,
                    )
                )
                required_character_ids = (
                    runner._scene_characters.character_ids_from_bindings(
                        enriched_scene_characters
                    )
                )
                required_character_names = (
                    runner._scene_characters.character_names_from_bindings(
                        enriched_scene_characters
                    )
                )
                character_block = runner._scene_characters.scene_character_prompt_block(
                    outputs, scene_data
                )
                scene_required_presence_block = (
                    runner._scene_characters.scene_character_required_presence_block(
                        outputs, scene_data
                    )
                )
                negative_block = runner._scene_characters.scene_character_negative_block(
                    outputs, scene_data
                )
                compact_trait_block = runner._scene_characters.scene_character_compact_trait_block(
                    outputs, scene_data
                )

                clean_visual_description = clean_image_prompt_text(visual_description) or scene_focus

                shot_anchor = (
                    f"scene title: {scene_title}, "
                    f"camera shot: {shot_type}, "
                    f"transition feeling: {transition}, "
                    f"visual focus: {clean_visual_description}"
                )

                story_anchor = f"story context: {text}"
                # scene_focus replaces empty visual_description so the
                # policy's scene_action_block always carries scene-specific
                # content, even when the storyboard LLM enrichment failed.
                policy_blocks = build_image_prompt_policy_blocks(
                    workflow_input=ctx.input,
                    outputs=profile_outputs,
                    visual_description=visual_description or scene_focus,
                    narration=text,
                    subject_hint=character_anchor,
                )

                scene_position_anchor = _scene_position_anchor(
                    scene_index=shot_index,
                    total=total_shots,
                    scene=scene_data or {"scene_title": scene_title},
                    narration_text=text,
                )
                anti_repeat_block = _anti_repeat_block(
                    scene_index=shot_index,
                    total=total_shots,
                )
                if not character_visual_profile:
                    character_visual_profile = policy_blocks.get("profile") or {}

                # Extract the first sentence of visual_identity as a color/appearance
                # prefix to place at the very start of the prompt — diffusion models
                # weight the beginning of the prompt most heavily, so pinning the
                # character's fixed color here significantly improves consistency.
                color_prefix = self._build_color_prefix(character_visual_profile)

                is_multi_character_scene = len(required_character_names) >= 2
                # In multi-character scenes the singular color_prefix puts only the
                # PRIMARY character at position 0 (e.g. "white rabbit, white fur").
                # The diffusion model then renders BOTH characters as the same
                # species — "two mirrored rabbits" instead of "rabbit + squirrel".
                # Override position 0 with a builder that names every species and
                # adds explicit "not two <species>" negatives.
                if is_multi_character_scene:
                    multi_prefix = self._build_multi_character_color_prefix(
                        character_visual_profiles,
                        enriched_scene_characters=enriched_scene_characters,
                    )
                    if multi_prefix:
                        color_prefix = multi_prefix

                # Roster reinforcement block — inserted immediately AFTER
                # the scene-specific text in multi-character scenes. The
                # storyboard's visual_description may name only one species
                # (e.g. "the squirrel jumps"), which then weights the
                # diffusion model toward rendering both characters as that
                # species. By following every scene-specific block with an
                # explicit "BOTH X and Y appear here, not two X, not two Y"
                # reinforcement, the single-species mention can't dominate.
                scene_multi_roster = (
                    _build_multi_character_roster_for_scene(enriched_scene_characters)
                    if is_multi_character_scene
                    else ""
                )
                # `scene_position_anchor` is placed right after color_prefix
                # so the early-prompt weight (most important for diffusion)
                # encodes THIS scene's identity before the shared
                # character-lock blocks. `anti_repeat_block` is appended at
                # the very end so the negative-style instruction caps the
                # sequence with explicit "do not duplicate previous scene".
                prompt_parts = [
                    color_prefix,
                    scene_position_anchor,
                    global_style_anchor,
                    shot_anchor,
                    scene_multi_roster,
                    character_anchor,
                    policy_blocks.get("visual_profile_block"),
                    policy_blocks.get("character_visual_profiles_block"),
                    character_block,
                    scene_required_presence_block,
                    policy_blocks.get("character_separation_block"),
                    policy_blocks.get("scene_action_block"),
                    scene_multi_roster,
                    story_anchor,
                    policy_blocks.get("subject_negative_block"),
                    negative_block,
                    anti_repeat_block,
                ]
                if is_multi_character_scene:
                    prompt_parts = [
                        color_prefix,
                        scene_position_anchor,
                        global_style_anchor,
                        compact_trait_block,
                        shot_anchor,
                        scene_multi_roster,
                        scene_required_presence_block,
                        character_block,
                        policy_blocks.get("character_visual_profiles_block"),
                        policy_blocks.get("character_separation_block"),
                        policy_blocks.get("scene_action_block"),
                        scene_multi_roster,
                        story_anchor,
                        negative_block,
                        anti_repeat_block,
                    ]

                prompt = ", ".join(
                    part for part in prompt_parts if part
                )

                prompts.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "characters": enriched_scene_characters,
                        "required_character_ids": required_character_ids,
                        "required_character_names": required_character_names,
                        "prompt": prompt,
                        "character_anchor": character_anchor_metadata,
                        "reference_images": character_anchor_metadata.get(
                            "reference_images"
                        )
                        or [],
                    }
                )

            _write_image_prompts_debug(getattr(ctx, "workflow_id", ""), prompts)
            return {
                "provider": "image_prompt_builder",
                "character_visual_profile": character_visual_profile,
                "character_visual_profiles": character_visual_profiles,
                "character_anchor": character_anchor_metadata,
                "prompts": prompts,
            }

        total_scenes = len(scenes)
        for scene_index, scene in enumerate(scenes):
            scene_id = str(scene.get("scene_id") or "").strip()
            narration = str(scene.get("narration", "")).strip()
            visual_description = str(scene.get("visual_description", "")).strip()
            shot_type = str(scene.get("shot_type", "medium")).strip()
            transition = str(scene.get("transition", "fade")).strip()
            scene_title = str(scene.get("scene_title", "")).strip()

            # Robust scene focus fallback so the per-scene visual content
            # is never blank even when storyboard LLM enrichment fails.
            scene_focus = _scene_action_fallback(
                visual_description=visual_description,
                narration=narration,
                scene_title=scene_title,
            )
            enriched_scene_characters = (
                runner._scene_characters.enriched_scene_characters_from_manifest(
                    outputs,
                    scene,
                )
            )
            required_character_ids = runner._scene_characters.character_ids_from_bindings(
                enriched_scene_characters
            )
            required_character_names = (
                runner._scene_characters.character_names_from_bindings(
                    enriched_scene_characters
                )
            )

            character_block = runner._scene_characters.scene_character_prompt_block(
                outputs, scene
            )
            scene_required_presence_block = (
                runner._scene_characters.scene_character_required_presence_block(
                    outputs, scene
                )
            )
            negative_block = runner._scene_characters.scene_character_negative_block(
                outputs, scene
            )
            compact_trait_block = runner._scene_characters.scene_character_compact_trait_block(
                outputs, scene
            )

            clean_visual_description = clean_image_prompt_text(visual_description) or scene_focus

            scene_anchor = (
                f"scene title: {scene_title}, "
                f"camera shot: {shot_type}, "
                f"transition feeling: {transition}, "
                f"visual focus: {clean_visual_description}"
            )

            story_anchor = f"story context: {narration}"
            policy_blocks = build_image_prompt_policy_blocks(
                workflow_input=ctx.input,
                outputs=profile_outputs,
                visual_description=visual_description or scene_focus,
                narration=narration,
                subject_hint=character_anchor,
            )

            scene_position_anchor = _scene_position_anchor(
                scene_index=scene_index,
                total=total_scenes,
                scene=scene,
                narration_text=narration,
            )
            anti_repeat_block = _anti_repeat_block(
                scene_index=scene_index,
                total=total_scenes,
            )
            if not character_visual_profile:
                character_visual_profile = policy_blocks.get("profile") or {}

            color_prefix = self._build_color_prefix(character_visual_profile)

            is_multi_character_scene = len(required_character_names) >= 2
            # Override position 0 with the multi-character species anchor when
            # there are 2+ required characters — see commentary in the shot
            # branch above. Without this, both characters render as the
            # primary species (mirrored rabbits / mirrored squirrels).
            if is_multi_character_scene:
                multi_prefix = self._build_multi_character_color_prefix(
                    character_visual_profiles
                )
                if multi_prefix:
                    color_prefix = multi_prefix

            # Roster reinforcement for multi-character scenes — placed
            # adjacent to per-scene text so the storyboard's potentially
            # single-species visual_description can't dominate. See
            # the helper docstring for the full failure-mode rationale.
            scene_multi_roster = (
                _build_multi_character_roster_for_scene(enriched_scene_characters)
                if is_multi_character_scene
                else ""
            )
            # scene_position_anchor goes early so this scene's identity
            # gets the most attention from the diffusion model; the
            # anti_repeat_block goes last so the negative-style demand
            # to differ from other scenes is the final instruction.
            prompt_parts = [
                color_prefix,
                scene_position_anchor,
                global_style_anchor,
                scene_anchor,
                scene_multi_roster,
                character_anchor,
                policy_blocks.get("visual_profile_block"),
                policy_blocks.get("character_visual_profiles_block"),
                character_block,
                scene_required_presence_block,
                policy_blocks.get("character_separation_block"),
                policy_blocks.get("scene_action_block"),
                scene_multi_roster,
                story_anchor,
                policy_blocks.get("subject_negative_block"),
                negative_block,
                anti_repeat_block,
            ]
            if is_multi_character_scene:
                prompt_parts = [
                    color_prefix,
                    scene_position_anchor,
                    global_style_anchor,
                    compact_trait_block,
                    scene_anchor,
                    scene_multi_roster,
                    scene_required_presence_block,
                    character_block,
                    policy_blocks.get("character_visual_profiles_block"),
                    policy_blocks.get("character_separation_block"),
                    policy_blocks.get("scene_action_block"),
                    scene_multi_roster,
                    story_anchor,
                    negative_block,
                    anti_repeat_block,
                ]

            prompt = ", ".join(
                part for part in prompt_parts if part
            )

            prompts.append(
                {
                    "scene_id": scene_id,
                    "scene_title": scene_title,
                    "characters": enriched_scene_characters,
                    "required_character_ids": required_character_ids,
                    "required_character_names": required_character_names,
                    "prompt": prompt,
                    "character_anchor": character_anchor_metadata,
                    "reference_images": character_anchor_metadata.get(
                        "reference_images"
                    )
                    or [],
                }
            )

        _write_image_prompts_debug(getattr(ctx, "workflow_id", ""), prompts)
        return {
            "provider": "image_prompt_builder",
            "character_visual_profile": character_visual_profile,
            "character_visual_profiles": character_visual_profiles,
            "character_anchor": character_anchor_metadata,
            "prompts": prompts,
        }

    def _build_multi_character_color_prefix(
        self,
        character_visual_profiles: Dict[str, Any],
        enriched_scene_characters: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Position-0 prefix for multi-character scenes.

        When a scene has 2+ required characters, the singular
        `_build_color_prefix(profile)` (which only sees the PRIMARY
        character) puts "white rabbit, white fur" at the start of the
        prompt — diffusion weights this most heavily and the model
        then renders BOTH characters as rabbits (or even mirrored
        copies of one rabbit). This builder pulls every character's
        species + the first color trait so the very first tokens of
        the prompt are "white long-eared rabbit and brown bushy-tailed
        squirrel, two different animal species". The explicit
        "not two <species>" negatives are critical — diffusion models
        respond strongly to that pattern when it appears early.
        """
        profiles = (character_visual_profiles or {}).get("profiles") or []
        # Defensive fallback: when the LLM-built character_visual_profiles
        # didn't produce >=2 entries (LLM error, key missing, partial
        # failure), fall back to the scene's enriched manifest bindings.
        # Those are reliably populated from the auto-built / user-defined
        # character_manifest and always have display_name + species when
        # the scene is multi-character. Without this, a single LLM hiccup
        # quietly drops us back to the singular color_prefix and the
        # diffusion model renders mirrored same-species characters.
        if not isinstance(profiles, list) or len(profiles) < 2:
            if (
                isinstance(enriched_scene_characters, list)
                and len(enriched_scene_characters) >= 2
            ):
                profiles = [
                    {
                        "species": str(c.get("species") or "").strip(),
                        "display_name": str(c.get("display_name") or "").strip(),
                        "subject": str(c.get("species") or c.get("display_name") or "").strip(),
                        "visual_identity": str(c.get("visual_identity") or "").strip(),
                        "must_keep": c.get("must_keep") or c.get("signature_traits") or [],
                    }
                    for c in enriched_scene_characters
                    if isinstance(c, dict)
                ]
            else:
                return ""

        COLOR_WORDS = {
            "red", "blue", "green", "yellow", "orange", "purple", "pink",
            "white", "black", "gray", "grey", "brown", "gold", "silver",
            "cream", "teal", "cyan", "magenta", "violet", "indigo",
            "红", "蓝", "绿", "黄", "橙", "紫", "粉", "白", "黑", "灰", "棕", "金",
        }

        labels: List[str] = []
        species_set: List[str] = []

        for profile in profiles:
            if not isinstance(profile, dict):
                continue

            must_keep = profile.get("must_keep") or []
            if not isinstance(must_keep, list):
                must_keep = []
            identity = str(profile.get("visual_identity") or "").strip()

            # Pick the first must_keep trait that carries a color word
            # so the label reads as "{color/trait} {species}" — e.g.
            # "white long-eared rabbit" or "brown bushy-tailed squirrel".
            color_trait = ""
            for trait in must_keep:
                t = str(trait or "").strip()
                if not t:
                    continue
                if any(c in t.lower() for c in COLOR_WORDS):
                    color_trait = t
                    break
            if not color_trait and identity:
                color_trait = identity.split(".")[0].strip()

            # English-friendly species label — Chinese species/display
            # from the auto-manifest gets ignored by Kolors etc.
            anchor_species = _english_label_for_character(profile)
            if not anchor_species:
                continue
            if anchor_species not in species_set:
                species_set.append(anchor_species)

            label = (
                f"{color_trait} {anchor_species}".strip()
                if color_trait
                else anchor_species
            )
            if label and label not in labels:
                labels.append(label)

        if len(labels) < 2:
            return ""

        # Build a species->count map from the same profile list so the
        # prefix language matches the actual required cast (handles
        # same-species casts like "rabbit + rabbit mom").
        counts = species_count_map(profiles)
        if not counts:
            return ""
        total = sum(counts.values())
        species_set = list(counts.keys())
        count_phrase = _format_species_count_phrase(counts)  # "2 rabbits and 1 squirrel"

        parts: List[str] = []
        # Lead with each character's color+species label so diffusion
        # weighs both at the front.
        parts.append(" and ".join(labels))
        parts.append(f"this image contains exactly {count_phrase}")
        parts.append(f"render exactly {total} animal subjects in total")

        # Per-species over-count negatives only. For required=1 squirrel
        # we forbid "two squirrels"; for required=2 rabbits we forbid
        # "three rabbits" but NEVER "two rabbits" — that would block
        # legitimate same-species output.
        count_words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
        for species, required in counts.items():
            plural = _pluralize(species)
            over = required + 1
            word = count_words.get(over, str(over))
            parts.append(f"not {word} {plural}")
            parts.append(f"no more than {required} {plural if required > 1 else species}")

        # Cross-species "do not swap" language only when the cast has
        # multiple distinct species.
        if len(species_set) >= 2:
            parts.append(
                f"distinct species required: {', '.join(species_set)}"
            )
            parts.append("do not draw both characters as the same species")
            parts.append("do not swap species between characters")

        return ", ".join(parts)

    def _build_color_prefix(self, profile: Dict[str, Any]) -> str:
        """Return a tight color+identity anchor prepended to every scene prompt.

        Diffusion models weight the beginning of the prompt most heavily.
        We extract the subject name and any must_keep items that contain a
        color word, then put "subject, color_trait1, color_trait2" first.
        This is more reliable than truncating visual_identity which often
        buries the color word past 120 characters.
        """
        if not profile:
            return ""

        COLOR_WORDS = {
            "red", "blue", "green", "yellow", "orange", "purple", "pink",
            "white", "black", "gray", "grey", "brown", "gold", "silver",
            "cream", "teal", "cyan", "magenta", "violet", "indigo",
            "红", "蓝", "绿", "黄", "橙", "紫", "粉", "白", "黑", "灰", "棕", "金",
        }

        subject = str(profile.get("subject") or "").strip()
        must_keep = profile.get("must_keep") or []
        if not isinstance(must_keep, list):
            must_keep = []

        # Pick must_keep entries that mention a color word (max 3)
        color_traits: List[str] = []
        for trait in must_keep:
            t = str(trait).strip()
            if not t:
                continue
            lower = t.lower()
            if any(c in lower for c in COLOR_WORDS) and t not in color_traits:
                color_traits.append(t)
            if len(color_traits) >= 3:
                break

        # Fallback: use first full sentence of visual_identity (no truncation)
        if not color_traits:
            identity = str(profile.get("visual_identity") or "").strip()
            if identity:
                first_sentence = identity.split(".")[0].strip()
                if len(first_sentence) > 10:
                    return first_sentence

        parts = [p for p in [subject] + color_traits if p]
        return ", ".join(parts) if parts else ""
