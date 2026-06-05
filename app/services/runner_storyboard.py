from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class RunnerStoryboardSupport:
    """Storyboard and sentence-shot helpers extracted from WorkflowRunner.

    Extracted as Step 9 of the runner refactor. This module owns the
    storyboard assembly and text-to-scene/shot splitting helpers while
    delegating shared story and character helpers back to WorkflowRunner.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def run_storyboard(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        runner = self._runner
        story_plan = runner._duration_story_plan(ctx.input.duration_sec)
        scene_count = story_plan["scene_count"]
        blueprints = runner._scene_blueprints(ctx, scene_count, outputs)
        story_out = outputs.get("story") or {}
        story_text = str(story_out.get("text") or "").strip()

        if story_text:
            paragraphs = self.split_story_for_scenes(story_text, scene_count)
        else:
            paragraphs = self.split_story_for_scenes(
                " ".join(runner._build_story_paragraphs(ctx, outputs)),
                scene_count,
            )
        total_duration_sec = ctx.input.duration_sec
        per_scene_duration = max(1, total_duration_sec // max(scene_count, 1))

        character_bindings = runner._scene_characters.scene_character_bindings(outputs)

        scenes: List[Dict[str, Any]] = []
        for index, blueprint in enumerate(blueprints, start=1):
            narration = paragraphs[index - 1] if index <= len(paragraphs) else ""
            scenes.append(
                {
                    "scene_id": f"scene_{index:02d}",
                    "scene_title": blueprint["scene_title"],
                    "visual_description": blueprint["visual_description"],
                    "narration": narration,
                    "duration_sec": per_scene_duration,
                    "shot_type": blueprint["shot_type"],
                    "transition": blueprint["transition"],
                    "characters": character_bindings,
                }
            )

        # Enrich visual_description per scene using LLM based on actual narration
        llm_descriptions = self._generate_scene_visual_descriptions(ctx, scenes, outputs)
        for scene in scenes:
            sid = scene["scene_id"]
            if sid in llm_descriptions:
                scene["visual_description"] = llm_descriptions[sid]

        return {
            "scene_count": scene_count,
            "total_duration_sec": total_duration_sec,
            "scenes": scenes,
        }

    def _generate_scene_visual_descriptions(
        self,
        ctx: Any,
        scenes: List[Dict[str, Any]],
        outputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Call LLM once to generate story-specific visual descriptions for all scenes.

        Returns a dict of scene_id -> visual_description.
        Falls back silently to empty dict (caller keeps blueprint description) on any error.
        """
        runner = self._runner
        try:
            api_key = runner._llm_api_key()
            model = runner._story_model_name()
            if not api_key or not model:
                return {}
        except Exception:
            return {}

        topic = str(getattr(ctx.input, "topic", "") or "").strip()
        visual_style = str(getattr(ctx.input, "visual_style", "") or "storybook").strip()

        try:
            manifest_items = runner._character_manifest_support.character_manifest_items(
                outputs or {}
            )
        except Exception:
            manifest_items = []

        character_lines: List[str] = []
        for item in manifest_items or []:
            name = str(item.get("display_name") or item.get("species") or "").strip()
            visual_id = str(item.get("visual_identity") or item.get("visual_traits") or "").strip()
            if name:
                character_lines.append(f"- {name}: {visual_id}" if visual_id else f"- {name}")

        scene_lines: List[str] = []
        for scene in scenes:
            sid = scene["scene_id"]
            title = str(scene.get("scene_title") or "").strip()
            narration = str(scene.get("narration") or "").strip()
            scene_lines.append(f'{sid} [{title}]: {narration or "(no narration)"}')

        # Distinct lighting palette per scene position keeps colors varied
        lighting_hints = [
            "golden morning sunlight, warm yellow tones",
            "bright noon sunlight, vivid green tones",
            "soft afternoon diffused light, blue-sky tones",
            "warm sunset glow, orange-red tones",
            "twilight dusk, blue-purple gradient tones",
            "soft moonlight or cozy indoor lamp, dreamy pastel tones",
        ]

        scene_instructions: List[str] = []
        for i, scene in enumerate(scenes):
            sid = scene["scene_id"]
            hint = lighting_hints[i % len(lighting_hints)]
            scene_instructions.append(f'- {sid}: use lighting palette "{hint}"')

        system_prompt = (
            "You are a visual art director for a children's animated picture book. "
            "Your job is to write concise image generation prompts in English. "
            "Each prompt must describe a vivid, distinct illustration scene."
        )

        # When the manifest lists >=2 characters, every scene description
        # must name every species — otherwise the downstream image
        # prompt's per-scene text only mentions one species, and the
        # diffusion model renders both required characters as that
        # species (e.g. two mirrored squirrels for a "rabbit+squirrel"
        # story).
        try:
            multi_character_mode = (
                isinstance(manifest_items, list) and len([
                    item for item in manifest_items
                    if isinstance(item, dict)
                    and (
                        str(item.get("display_name") or "").strip()
                        or str(item.get("species") or "").strip()
                    )
                ]) >= 2
            )
        except Exception:
            multi_character_mode = False

        character_naming_rule = ""
        if multi_character_mode:
            character_naming_rule = (
                "5. EVERY scene description MUST explicitly name ALL of the "
                "required characters listed above. If the narration mentions "
                "only one character explicitly, you must still include the "
                "other character(s) by their species or display name in the "
                "description (e.g. 'while the squirrel watches from behind a "
                "tree'). Do NOT write a scene that only names one species — "
                "this is the most common failure mode.\n"
            )

        user_prompt = (
            f"Story topic: {topic}\n"
            f"Art style: {visual_style} illustration, cute chibi anime, soft warm colors\n"
            f"Characters:\n" + ("\n".join(character_lines) or "- (infer from topic)") + "\n\n"
            f"Lighting requirements per scene (MUST follow):\n"
            + "\n".join(scene_instructions) + "\n\n"
            f"Scenes (scene_id [title]: narration):\n"
            + "\n".join(scene_lines) + "\n\n"
            "For each scene write a visual_description (2-3 sentences in English) that:\n"
            "1. START with the character's SPECIFIC PHYSICAL ACTION derived from the narration.\n"
            "   Use strong motion verbs: sprinting, leaping, tumbling, celebrating, crouching, panting, waving, etc.\n"
            "   NEVER start with environment. NEVER describe characters as just 'standing' or 'sitting' unless the narration explicitly says so.\n"
            "   Example: 'The rabbit dashes forward with powerful leaps, ears streaming behind, while the turtle plods steadily on the dusty track.'\n"
            "2. Then describe the SPECIFIC environment/location matching the narration.\n"
            "3. End with the required lighting palette for that scene.\n"
            "4. Each scene must be visually DISTINCT from all others — different action, location, and color.\n"
            + character_naming_rule +
            "\n"
            "Return ONLY valid JSON, no markdown:\n"
            '{"scenes": [{"scene_id": "scene_01", "visual_description": "..."}, ...]}'
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1200,
        }

        def _parse_descriptions(raw_content: str) -> Dict[str, str]:
            content = raw_content
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            result = json.loads(content)
            out: Dict[str, str] = {}
            for item in result.get("scenes") or []:
                sid = str(item.get("scene_id") or "").strip()
                desc = str(item.get("visual_description") or "").strip()
                if sid and desc:
                    out[sid] = desc
            return out

        try:
            timeout = runner._story_timeout_seconds()
            try:
                content = runner._call_llm_chat(
                    api_base_url=runner._llm_api_base_url(),
                    api_key=api_key,
                    payload=payload,
                    timeout=timeout,
                )
            except Exception:
                fallback_url = runner._llm_fallback_api_base_url()
                fallback_key = runner._llm_fallback_api_key()
                if not fallback_url or not fallback_key:
                    raise
                fallback_payload = dict(payload)
                fallback_payload["model"] = runner._llm_fallback_model_name()
                content = runner._call_llm_chat(
                    api_base_url=fallback_url,
                    api_key=fallback_key,
                    payload=fallback_payload,
                    timeout=timeout,
                )
            return _parse_descriptions(content)

        except Exception:
            return {}

    def split_story_for_scenes(self, text: str, scene_count: int) -> List[str]:
        normalized = " ".join(str(text or "").split()).strip()
        if scene_count <= 0:
            return []
        if not normalized:
            return []

        sentences = self.split_story_sentences(normalized)
        if len(sentences) >= scene_count:
            chunks: List[str] = []
            for index in range(scene_count):
                start = int(index * len(sentences) / scene_count)
                end = int((index + 1) * len(sentences) / scene_count)
                if end <= start:
                    end = start + 1
                chunk = "".join(sentences[start:end]).strip()
                if chunk:
                    chunks.append(chunk)
            deduped = self.dedupe_adjacent_text(chunks)
            if len(deduped) == scene_count:
                return deduped

        return self.split_text_by_char_balance(normalized, scene_count)

    def split_text_by_char_balance(self, text: str, scene_count: int) -> List[str]:
        normalized = " ".join(str(text or "").split()).strip()
        if scene_count <= 0 or not normalized:
            return []

        chunks: List[str] = []
        cursor = 0
        punctuation = "。！？；!?;"
        text_len = len(normalized)

        for index in range(scene_count):
            remaining_slots = scene_count - index
            remaining_chars = text_len - cursor
            if remaining_chars <= 0:
                break

            target_end = cursor + max(1, remaining_chars // remaining_slots)
            if index == scene_count - 1:
                end = text_len
            else:
                window_start = max(cursor + 1, target_end - 10)
                window_end = min(text_len, target_end + 12)
                end = 0
                for pos in range(target_end, window_end):
                    if normalized[pos - 1] in punctuation:
                        end = pos
                        break
                if not end:
                    for pos in range(target_end, window_start, -1):
                        if normalized[pos - 1] in punctuation:
                            end = pos
                            break
                if not end:
                    end = min(text_len, target_end)

            chunk = normalized[cursor:end].strip()
            if chunk:
                chunks.append(chunk)
            cursor = end

        return self.dedupe_adjacent_text(chunks)

    def dedupe_adjacent_text(self, items: List[str]) -> List[str]:
        deduped: List[str] = []
        for item in items:
            text = " ".join(str(item or "").split()).strip()
            if not text:
                continue
            if deduped and text == deduped[-1]:
                continue
            deduped.append(text)
        return deduped

    def run_sentence_shots(self, ctx: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
        storyboard = outputs.get("storyboard") or {}
        scenes = storyboard.get("scenes") or []

        items: List[Dict[str, Any]] = []
        shot_index = 1

        for scene in scenes:
            scene_id = str(scene.get("scene_id") or "").strip()
            scene_title = str(scene.get("scene_title") or "").strip()
            visual_description = str(scene.get("visual_description") or "").strip()
            narration = str(scene.get("narration") or "").strip()
            shot_type = str(scene.get("shot_type") or "medium").strip()
            transition = str(scene.get("transition") or "fade").strip()

            sentence_list = self.split_story_sentences(narration)
            if not sentence_list and narration:
                sentence_list = [narration]

            for sentence in sentence_list:
                shot_id = f"shot_{shot_index:02d}"
                items.append(
                    {
                        "shot_id": shot_id,
                        "scene_id": scene_id,
                        "scene_title": scene_title,
                        "visual_description": visual_description,
                        "shot_type": shot_type,
                        "transition": transition,
                        "text": sentence,
                        "subtitle_text": sentence,
                        "audio_text": sentence,
                    }
                )
                shot_index += 1

        return {
            "enabled": True,
            "shot_count": len(items),
            "items": items,
        }

    def split_story_sentences(self, text: str) -> List[str]:
        normalized = str(text or "").replace("\n", " ").strip()
        if not normalized:
            return []

        sentences: List[str] = []
        current: List[str] = []
        hard_break_chars = {"。", "！", "？", "；", "!", "?", ";"}

        for ch in normalized:
            current.append(ch)
            if ch in hard_break_chars:
                sentence = "".join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []

        tail = "".join(current).strip()
        if tail:
            sentences.append(tail)

        merged: List[str] = []
        for sentence in sentences:
            compact = " ".join(sentence.split()).strip()
            if not compact:
                continue

            if merged and len(compact) < 8:
                merged[-1] = f"{merged[-1]}{compact}"
            else:
                merged.append(compact)

        if not merged and normalized:
            merged = [normalized]

        return merged
