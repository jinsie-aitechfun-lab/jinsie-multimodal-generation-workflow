from __future__ import annotations

from typing import Any, Dict, List


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

        return {
            "scene_count": scene_count,
            "total_duration_sec": total_duration_sec,
            "scenes": scenes,
        }

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
