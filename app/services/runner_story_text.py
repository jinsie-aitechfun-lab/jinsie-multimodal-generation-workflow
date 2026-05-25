from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.story_retry_policy import story_text_has_quality_issues


class RunnerStoryTextSupport:
    """Story text plans, labels, sanitization, and template paragraphs.

    Extracted as Step 8 of the runner refactor. These helpers are data-only
    story utilities used by story generation, story retry policy, storyboard,
    and image/video progress metadata.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def scene_count(self, duration_sec: int) -> int:
        if duration_sec <= 60:
            return 6
        if duration_sec <= 120:
            return 12
        return 18

    def duration_story_plan(self, duration_sec: int) -> Dict[str, int]:
        supported = [
            {
                "duration_sec": 60,
                "scene_count": 6,
                "target_min_chars": 250,
                "target_max_chars": 310,
                "target_chars": 280,
            },
            {
                "duration_sec": 120,
                "scene_count": 12,
                "target_min_chars": 560,
                "target_max_chars": 700,
                "target_chars": 650,
            },
            {
                "duration_sec": 180,
                "scene_count": 18,
                "target_min_chars": 840,
                "target_max_chars": 1050,
                "target_chars": 960,
            },
        ]
        for item in supported:
            if duration_sec == item["duration_sec"]:
                return dict(item)

        scene_count = self.scene_count(duration_sec)
        for item in supported:
            if scene_count == item["scene_count"]:
                plan = dict(item)
                plan["duration_sec"] = duration_sec
                return plan

        nearest = min(
            supported,
            key=lambda item: abs(duration_sec - int(item["duration_sec"])),
        )
        plan = dict(nearest)
        plan["duration_sec"] = duration_sec
        return plan

    def sanitize_llm_story_text(self, text: str, topic: str = "") -> str:
        raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        topic_text = str(topic or "").strip()

        lines = []
        for line in raw.split("\n"):
            item = " ".join(str(line or "").split()).strip()
            if not item:
                continue

            lower = item.lower()

            if lower in {"user", "assistant", "system", "role", "content"}:
                continue

            if topic_text and item == topic_text:
                continue

            if item.isdigit():
                continue

            # Drop short polluted fragments such as "小 1".
            if len(item) <= 12 and any(ch.isdigit() for ch in item):
                continue

            # Drop obvious role-like fragments.
            if lower.startswith(("user:", "assistant:", "system:", "role:")):
                continue

            lines.append(item)

        cleaned = "\n".join(lines).strip()

        # If the model echoed a noisy title/prefix before the first real story
        # sentence, keep text from the first reasonably long Chinese narrative
        # sentence.
        sentence_markers = ["有一天", "在一个", "很久以前", "清晨", "傍晚", "一天"]
        for marker in sentence_markers:
            pos = cleaned.find(marker)
            if pos > 0:
                prefix = cleaned[:pos]
                if (
                    "user" in prefix.lower()
                    or "assistant" in prefix.lower()
                    or topic_text in prefix
                    or any(ch.isdigit() for ch in prefix)
                ):
                    cleaned = cleaned[pos:].strip()
                break

        return cleaned

    def story_text_has_blocked_tokens(self, text: str) -> bool:
        normalized = str(text or "").lower()
        blocked_tokens = [
            " user",
            " assistant",
            " system",
            "role=",
            "species=",
            "traits=",
            "forbid=",
            "kuk",
        ]
        return any(token in normalized for token in blocked_tokens)

    def story_text_char_count(self, text: str) -> int:
        return len("".join(str(text or "").split()))

    def story_text_has_quality_issues(self, text: str) -> bool:
        return story_text_has_quality_issues(text)

    def audience_label(self, audience: str) -> str:
        mapping = {
            "children": "小朋友",
            "kids": "小朋友",
            "general": "所有人",
            "family": "亲子家庭",
            "teen": "青少年",
        }
        return mapping.get(audience.lower(), audience)

    def tone_label(self, tone: str) -> str:
        mapping = {
            "warm": "温暖",
            "funny": "轻松有趣",
            "healing": "治愈",
            "adventure": "冒险",
            "gentle": "柔和",
        }
        return mapping.get(tone.lower(), tone)

    def visual_style_label(self, visual_style: str) -> str:
        mapping = {
            "storybook": "绘本",
            "illustration": "插画",
            "cartoon": "卡通",
            "animation": "动画",
        }
        return mapping.get(visual_style.lower(), visual_style)

    def character_style_label(self, character_style: str) -> str:
        mapping = {
            "animal": "小动物",
            "human": "人物",
            "fantasy": "奇幻角色",
        }
        return mapping.get(character_style.lower(), character_style)

    def build_story_paragraphs(
        self,
        ctx: Any,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        runner = self._runner
        topic = runner._clean_story_topic(ctx.input.topic) or "一个温暖的童话故事"
        tone_label = self.tone_label(ctx.input.tone)

        main_character_display = runner._main_character_display_label(ctx, outputs)
        secondary_character_display = runner._secondary_character_display_label(
            ctx, outputs
        )
        has_secondary_character = runner._has_secondary_character(ctx, outputs)
        story_plan = self.duration_story_plan(ctx.input.duration_sec)

        if has_secondary_character:
            paragraph_1 = (
                f"在一个安静又明亮的清晨，围绕“{topic}”展开了一段{tone_label}的小故事。"
                f"故事的主角是可爱的{main_character_display}，它和朋友{secondary_character_display}一起踏上了新的旅程。"
            )
            paragraph_2 = (
                f"起初，一切都很顺利，可没过多久，{main_character_display}遇到了一点小麻烦。"
                f"{secondary_character_display}陪在它身边，一起观察周围的变化，也一起思考接下来该怎么办。"
            )
            paragraph_3 = (
                f"在一路上的观察、尝试和彼此鼓励下，{main_character_display}慢慢鼓起勇气，"
                f"{secondary_character_display}也主动帮忙，它们一点点找到了解决问题的方法。"
            )
            paragraph_4 = (
                f"最后，{main_character_display}和{secondary_character_display}顺利完成了这段旅程，"
                f"也一起收获了陪伴、勇气和成长。"
                f"它们带着这份温暖回到熟悉的地方。"
            )
            paragraphs = [paragraph_1, paragraph_2, paragraph_3, paragraph_4]
            if story_plan["scene_count"] >= 12:
                paragraphs.extend(
                    [
                        (
                            f"它们没有急着放弃，而是把发现到的线索一条条记在心里：哪里有声音，哪里有光，"
                            f"哪里又藏着和“{topic}”有关的小秘密。"
                        ),
                        (
                            f"{main_character_display}负责大胆尝试，{secondary_character_display}负责提醒它慢一点看清楚。"
                            f"两个朋友配合得越来越好，原本让人担心的麻烦，也慢慢变成了可以解决的任务。"
                        ),
                        (
                            f"当新的困难再次出现时，它们已经不再慌张，而是先互相鼓励，再一步一步行动。"
                            f"它们明白，只要愿意倾听、观察和合作，答案就会在路上慢慢出现。"
                        ),
                    ]
                )
            if story_plan["scene_count"] >= 18:
                paragraphs.extend(
                    [
                        (
                            f"后来，它们遇见了需要帮助的伙伴，便把刚学会的方法分享出去。"
                            f"大家一起试了几次，虽然中间也有小小的失误，却没有人责怪谁。"
                        ),
                        (
                            f"夕阳把路边照得柔和明亮，{main_character_display}回头看见自己走过的每一步，"
                            f"忽然发现勇气不是一下子变大的，而是在每一次认真尝试里慢慢长出来的。"
                        ),
                        (
                            f"{secondary_character_display}轻轻笑了起来，说这趟旅程最珍贵的不是找到答案，"
                            f"而是它们学会了在需要的时候伸出手，也学会了相信朋友和自己。"
                        ),
                    ]
                )
            return paragraphs

        paragraph_1 = (
            f"在一个安静又明亮的清晨，围绕“{topic}”展开了一段{tone_label}的小故事。"
            f"故事的主角是一位可爱的{main_character_display}，它带着好奇心走进了新的旅程。"
        )
        paragraph_2 = (
            f"起初，一切都很顺利，可没过多久，这位{main_character_display}就遇到了一点小麻烦。"
            f"它有些紧张，也有些犹豫，不知道该不该继续往前走。"
        )
        paragraph_3 = (
            f"但在一路上的观察、尝试和他人的帮助下，这位{main_character_display}慢慢鼓起勇气，"
            f"一点点找到了解决问题的方法，也学会了相信自己。"
        )
        paragraph_4 = (
            f"最后，这位{main_character_display}顺利完成了这段旅程，也收获了陪伴、勇气和成长。"
            f"它带着这份温暖回到熟悉的地方。"
        )

        paragraphs = [paragraph_1, paragraph_2, paragraph_3, paragraph_4]
        if story_plan["scene_count"] >= 6:
            paragraphs.append(
                f"它停下来深深吸了一口气，开始认真观察周围的声音、颜色和脚印。"
                f"虽然答案还没有马上出现，但这位{main_character_display}已经不再像刚开始那样害怕了。"
            )
        if story_plan["scene_count"] >= 12:
            paragraphs.extend(
                [
                    (
                        f"它停下来仔细观察，发现每一个细小变化都像一条线索，正悄悄指向“{topic}”的答案。"
                        f"它把这些线索连在一起，心里的害怕也一点点变小了。"
                    ),
                    (
                        f"接着，它试着换一种办法前进：先做容易的事，再面对最难的那一步。"
                        f"途中有人给它鼓励，也有人提醒它别忘了休息和思考。"
                    ),
                    (
                        f"当问题再次变得复杂时，它没有重复旧办法，而是把新的发现和以前的经验放在一起。"
                        f"这一次，它终于看见了真正需要解决的地方。"
                    ),
                ]
            )
        if story_plan["scene_count"] >= 18:
            paragraphs.extend(
                [
                    (
                        f"它还遇见了正在为同样事情烦恼的小伙伴，便把自己的发现轻轻说给对方听。"
                        f"两个身影并肩往前走，路也好像变得宽了一些。"
                    ),
                    (
                        f"天色渐渐温柔下来，它回想起出发时的犹豫，发现自己已经能够安静地面对未知。"
                        f"那些小小的尝试，原来都在悄悄帮助它长大。"
                    ),
                    (
                        f"回到熟悉的地方后，它把这段经历珍藏在心里。"
                        f"从那以后，每当新的旅程开始，它都会记得先看一看、想一想，再带着勇气迈出脚步。"
                    ),
                ]
            )

        return paragraphs
