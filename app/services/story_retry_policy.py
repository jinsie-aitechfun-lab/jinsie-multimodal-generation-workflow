from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple
from urllib import request as urllib_request

from app.services.llm_output_sanitizer import parse_story_payload
from app.services.story_subject_extractor import (
    normalize_story_topic as extract_normalize_story_topic,
    story_main_subject as extract_story_main_subject,
)


def normalize_story_topic(topic: str) -> str:
    return extract_normalize_story_topic(topic)


def story_main_subject(topic: str) -> str:
    return extract_story_main_subject(topic)

def build_story_closing_sentence(topic: str) -> str:
    clean_topic = normalize_story_topic(topic)
    subject = story_main_subject(clean_topic)
    actor = "它" if subject == "主角" else subject

    if "骑自行车" in clean_topic or "自行车" in clean_topic:
        return f"{actor}再次扶稳车把，沿着小路慢慢前进，比刚开始时更稳了一些。"

    if "雪人" in clean_topic or "堆雪" in clean_topic:
        return f"{actor}认真看着整理好的雪人，把这次耐心完成的小任务记在心里。"

    return f"{actor}回头看看一路遇见的朋友和风景，把这次勇敢的尝试记在了心里。"


def story_text_matches_topic(text: str, topic: str) -> bool:
    clean_topic = normalize_story_topic(topic)
    normalized_text = " ".join(str(text or "").split())

    keyword_groups: list[tuple[str, tuple[str, ...]]] = [
        ("雪糕", ("雪糕", "冰淇淋")),
        ("冰淇淋", ("雪糕", "冰淇淋")),
        ("自行车", ("自行车",)),
        ("雪人", ("雪人", "雪")),
        ("堆雪", ("雪人", "雪")),
        ("怪兽", ("怪兽",)),
        ("奥特曼", ("奥特曼",)),
        ("小汽车", ("小汽车",)),
        ("小恐龙", ("小恐龙", "恐龙")),
    ]

    for topic_keyword, text_keywords in keyword_groups:
        if topic_keyword in clean_topic:
            return any(keyword in normalized_text for keyword in text_keywords)

    return True


def story_subject_is_protagonist(text: str, topic: str) -> bool:
    clean_topic = normalize_story_topic(topic)
    subject = story_main_subject(clean_topic)
    normalized_text = " ".join(str(text or "").split())
    for prefix in ("这位", "这辆", "这个", "那位", "那辆", "那个"):
        normalized_text = normalized_text.replace(f"{prefix}{subject}", subject)

    if not subject or subject == "主角":
        return True

    if subject not in normalized_text:
        return False

    prop_risk_subjects = {
        "小汽车",
        "小书包",
        "小云朵",
        "小机器人",
        "自行车",
        "雪人",
    }

    if subject not in prop_risk_subjects:
        return True

    prop_only_patterns = [
        rf"(一场|这次|一次|关于|有关){re.escape(subject)}(旅行|冒险|故事|活动)",
        rf"(开着|坐上|坐在|驾驶|发动|乘坐|搭乘|开动|开进|开到){re.escape(subject)}",
        rf"{re.escape(subject)}(下避雨|旁边|里面|里|上面|下面)",
        rf"{re.escape(subject)}(只是|成为|作为)?(交通工具|道具|背景|车辆)",
    ]

    if any(re.search(pattern, normalized_text) for pattern in prop_only_patterns):
        return False

    subject_with_optional_name = rf"{re.escape(subject)}[\u4e00-\u9fff]{{0,4}}"

    subject_actor_patterns = [
        rf"{subject_with_optional_name}(叫|名叫|是一辆|是一个|喜欢|想要|决定|准备|开始|学会|明白)",
        rf"{subject_with_optional_name}(出发|上路|启程|驶出|驶向|驶过|穿过|停下|继续|回家)",
        rf"{subject_with_optional_name}(看见|发现|遇见|听见|想到|想了想|说|问|回答)",
        rf"{subject_with_optional_name}(帮助|陪伴|保护|完成|记住|鼓起勇气)",
        rf"{subject_with_optional_name}带着",
        rf"{subject_with_optional_name}沿着",
        rf"{subject_with_optional_name}慢慢",
        rf"{subject_with_optional_name}终于",
    ]

    return any(re.search(pattern, normalized_text) for pattern in subject_actor_patterns)

def build_story_topic_anchor_sentence(topic: str) -> str:
    clean_topic = normalize_story_topic(topic)
    subject = story_main_subject(clean_topic)

    if "雪糕" in clean_topic or "冰淇淋" in clean_topic:
        return f"{subject}重新捧起雪糕，小心地尝了一口，也学会了和朋友分享清凉。"

    if "自行车" in clean_topic:
        return f"{subject}扶稳自行车，继续慢慢练习，终于比刚开始骑得更稳了。"

    if "雪人" in clean_topic or "堆雪" in clean_topic:
        return f"{subject}认真整理雪人的帽子和围巾，让雪人稳稳站在雪地里。"

    if "怪兽" in clean_topic:
        return f"{subject}勇敢面对小怪兽，也学会了用善意保护大家。"

    if "旅行" in clean_topic:
        return f"{subject}继续完成这次旅行，把一路上的风景都记在心里。"

    return build_story_closing_sentence(clean_topic)


def build_story_completion_sentences(topic: str) -> list[str]:
    clean_topic = normalize_story_topic(topic)
    subject = story_main_subject(clean_topic)
    actor = "它" if subject == "主角" else subject
    closing_sentence = build_story_closing_sentence(clean_topic)

    if "骑自行车" in clean_topic or "自行车" in clean_topic:
        return [
            f"{actor}一次次扶正车把，慢慢找到平衡，也不再害怕摔倒。",
            f"它沿着小路继续练习，虽然速度不快，却每一步都比刚开始更稳。",
            f"朋友们在旁边鼓励它，{actor}也越来越相信自己能够做到。",
            closing_sentence,
        ]

    if "旅行" in clean_topic:
        return [
            f"{actor}继续向前出发，看见了新的风景，也遇到了愿意互相帮助的朋友。",
            f"路上虽然有一点小困难，但{actor}没有着急，而是停下来认真想办法。",
            f"它慢慢调整方向，继续沿着小路前进，把这次旅行变成了一次勇敢的尝试。",
            f"沿途的风景一点点展开，{actor}也学会了在陌生地方保持耐心和好奇。",
            f"当它回头看见走过的路时，才发现自己已经比出发时更勇敢了。",
            closing_sentence,
        ]

    if "雪糕" in clean_topic or "冰淇淋" in clean_topic:
        return [
            f"{actor}小心地捧着雪糕，也学会了和朋友一起分享清凉和快乐。",
            closing_sentence,
        ]

    if "雪人" in clean_topic or "堆雪" in clean_topic:
        return [
            f"{actor}又认真整理了雪人的帽子和围巾，让雪人稳稳地站在雪地里。",
            closing_sentence,
        ]

    if "怪兽" in clean_topic:
        return [
            f"{actor}没有急着放弃，而是勇敢地保护大家，也学会了用善意解决问题。",
            closing_sentence,
        ]

    return [
        f"{actor}停下来观察周围，和伙伴们一起把线索重新整理了一遍。",
        "新的发现让前方的小路变得清楚起来，原本让人担心的麻烦也有了答案。",
        closing_sentence,
    ]


def story_text_has_quality_issues(text: str) -> bool:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return True

    suspicious_tokens = [
        "mexico",
        "undefined",
        "null",
        "nan",
        "小ěr",
        "小er",
        "xiaoer",
        "雪里",
        "铲铲",
        "�",
    ]
    lower = normalized.lower()
    if any(token in lower for token in suspicious_tokens):
        return True

    if re.search(r"\d+\s*秒", normalized):
        return True

    has_chinese = re.search(r"[\u4e00-\u9fff]", normalized) is not None
    if has_chinese and re.search(r"[A-Za-z]{2,}", normalized):
        return True

    if re.search(r"[A-Za-z][\u4e00-\u9fff]|[\u4e00-\u9fff][A-Za-z]", normalized):
        return True

    repeated_fragments = [
        "在在",
        "的的",
        "了了",
        "着着",
        "再再",
        "它它",
        "子子",
        "米米米",
        "梯梯",
        "小小桃",
        "想了想，，",
        "，，",
        "。。",
        "、、",
        "！！",
        "？？",
    ]
    if any(fragment in normalized for fragment in repeated_fragments):
        return True

    if re.search(r"[^\w\s\u4e00-\u9fff，。！？、；：“”‘’（）《》—…,.!?;:'\"()\-]{3,}", normalized):
        return True

    for index in range(len(normalized) - 2):
        a, b, c = normalized[index], normalized[index + 1], normalized[index + 2]
        if a == b == c and a not in {"哈", "啦", "啊", "嗯"}:
            return True

    return False


def validate_story_text(
    runner: Any,
    text: str,
    topic: str,
    story_plan: Dict[str, int],
) -> Tuple[str, List[str]]:
    cleaned_text = runner._sanitize_llm_story_text(text, topic)

    looks_like_struct = (
        cleaned_text.startswith("{")
        or cleaned_text.startswith("[")
        or cleaned_text.startswith("{'")
        or cleaned_text.startswith("['")
        or re.search(r"(?i)scene\s*\d+\s*[:：]", cleaned_text) is not None
        or re.search(r"[\[【（(]?\s*(画面|分镜)\s*[一二三四五六七八九十\d]+\s*[\]】）)]?\s*[:：]?", cleaned_text) is not None
        or re.search(r"(^|\n)\s*[^\n]{1,12}\s*[:：]", cleaned_text) is not None
    )

    story_char_count = runner._story_text_char_count(cleaned_text)
    duration_sec = int(story_plan.get("duration_sec") or 0)
    target_max_chars = int(story_plan.get("target_max_chars") or 0)
    min_tolerance = 10 if duration_sec <= 60 else 20
    effective_target_min = max(0, int(story_plan.get("target_min_chars") or 0) - min_tolerance)
    too_short = story_char_count < effective_target_min
    # too_long fires on either:
    #   1. raw char count exceeds the preset's target_max_chars, OR
    #   2. predicted audio duration (chars / 5 chars-per-sec TTS rate)
    #      exceeds the target duration by more than 5% — catches the case
    #      where the LLM ignores target_chars and produces ~960 chars for
    #      every preset, which makes 120s/180s land at ~200s.
    # Previously this check was gated on duration_sec <= 60, leaving 120s
    # and 180s presets with no upper-bound enforcement at all.
    char_overshoot = target_max_chars > 0 and story_char_count > target_max_chars
    audio_overshoot = (
        duration_sec > 0
        and story_char_count > int(duration_sec * 5.0 * 1.05)
    )
    too_long = char_overshoot or audio_overshoot
    has_blocked_tokens = runner._story_text_has_blocked_tokens(cleaned_text)
    has_quality_issues = story_text_has_quality_issues(cleaned_text)
    has_topic_mismatch = not story_text_matches_topic(cleaned_text, topic)
    has_subject_not_protagonist = not story_subject_is_protagonist(
        cleaned_text,
        topic,
    )

    invalid_reasons: List[str] = []
    if not cleaned_text:
        invalid_reasons.append("empty_text")
    if looks_like_struct:
        invalid_reasons.append("structured_output")
    if too_short:
        invalid_reasons.append("too_short")
    if too_long:
        invalid_reasons.append("too_long")
    if has_blocked_tokens:
        invalid_reasons.append("blocked_tokens")
    if has_quality_issues:
        invalid_reasons.append("quality_issues")
    if has_topic_mismatch:
        invalid_reasons.append("topic_mismatch")
    if has_subject_not_protagonist:
        invalid_reasons.append("subject_not_protagonist")

    return cleaned_text, invalid_reasons


def evaluate_story_retry_mode(
    story_char_count: int,
    invalid_reasons: List[str],
    story_plan: Dict[str, int],
) -> str:
    target_min = int(story_plan.get("target_min_chars") or 0)
    target_max = int(story_plan.get("target_max_chars") or 0)

    # Structured output means the model returned JSON/outline/scene-like content.
    # In that case, regenerate a clean story instead of preserving the broken shape.
    if "structured_output" in invalid_reasons:
        return "repair_regenerate"

    # Length issues should still control compression/expansion strength even when
    # quality_issues is also present. Otherwise the retry may only clean text
    # without fixing the duration/character-count problem.
    if "too_long" in invalid_reasons:
        over_limit = story_char_count - target_max
        if over_limit <= 40:
            return "light_compress"
        if over_limit <= 120:
            return "medium_compress"
        return "rewrite_short_complete"

    if "too_short" in invalid_reasons:
        # If the text is both too short and polluted, ignore the broken fragment
        # and regenerate a complete clean story.
        if "quality_issues" in invalid_reasons:
            return "repair_regenerate"

        under_limit = target_min - story_char_count
        if under_limit <= 40:
            return "light_expand"
        return "rewrite_complete"

    if "quality_issues" in invalid_reasons:
        return "repair_regenerate"

    if "subject_not_protagonist" in invalid_reasons:
        return "repair_regenerate"

    return "repair_regenerate"


def build_story_retry_instruction(
    retry_mode: str,
    target_min: int,
    target_max: int,
    target_chars: int,
    retry_target_max: int,
) -> str:
    if retry_mode == "light_compress":
        return (
            "The story is only slightly too long. Lightly compress it while preserving the original main plot. "
            f"Keep the revised story between {target_min} and {target_max} Chinese characters, preferably about {target_chars}. "
            "Remove only redundant adjectives, repeated actions, and unnecessary dialogue. "
            "Also clean abnormal spaces, repeated words, broken fragments, mixed Latin characters, and abnormal punctuation. "
            "Do not turn it into a summary. Keep it as a complete short story."
        )

    if retry_mode == "medium_compress":
        return (
            "The story is moderately too long. Compress it into a tighter Chinese children's story. "
            f"Keep the revised story between {target_min} and {retry_target_max} Chinese characters, preferably about {target_chars}. "
            "Keep one main character, one goal, one small problem, one action, one result, and one warm ending. "
            "Remove side plots, extra characters, repeated descriptions, and long dialogue. "
            "Also clean abnormal spaces, repeated words, broken fragments, mixed Latin characters, and abnormal punctuation. "
            "Do not summarize as bullet points. Return a complete story."
        )

    if retry_mode == "rewrite_short_complete":
        return (
            "The original story is far too long. Do not compress it sentence by sentence. "
            "Rewrite it as a short complete Chinese children's story based on the topic. "
            f"Keep the final story between {target_min} and {retry_target_max} Chinese characters, preferably about {target_chars}. "
            "The story must include exactly one clear goal, one small difficulty or discovery, one action, one result, and one warm ending. "
            "Do not keep side plots, extra helpers, long conversations, or secondary adventures from the original. "
            "Also clean abnormal spaces, repeated words, broken fragments, mixed Latin characters, and abnormal punctuation. "
            "Return only the final story text."
        )

    if retry_mode == "light_expand":
        return (
            "The story is slightly too short. Lightly expand it into a complete Chinese children's story. "
            f"Keep the revised story between {target_min} and {target_max} Chinese characters, preferably about {target_chars}. "
            "Add a small difficulty, one action, and a warm ending without adding irrelevant characters."
        )

    if retry_mode == "rewrite_complete":
        return (
            "The original story is too short or incomplete. Do not continue the broken fragment. "
            "Rewrite it as a short complete Chinese children's story based on the topic. "
            f"Strictly keep the final story between {target_min} and {target_max} Chinese characters, preferably no more than {retry_target_max}. "
            "Use 4 to 5 short sentences only. "
            "The story must include one main character, one clear goal, one small difficulty or discovery, one action, one result, and one warm ending. "
            "Do not add extra friends, side plots, long dialogue, photo-taking, or repeated warm summaries. "
            "Remove abnormal punctuation, repeated punctuation, broken fragments, and mixed Latin characters. "
            "Return only the final clean story text."
        )

    return (
        "The original story is corrupted or malformed. Regenerate a clean Chinese children's story based on the topic instead of continuing the corrupted text. "
        f"Strictly keep the revised story between {target_min} and {target_max} Chinese characters, preferably about {target_chars}. "
        "Remove all scene labels, English words, Latin characters, broken fragments, repeated characters, and abnormal punctuation. "
        "Keep a complete beginning, development, small problem or discovery, action, resolution, and warm ending. "
        "Return only the final clean story text."
    )


def repair_retry_story_text(
    runner: Any,
    text: str,
    topic: str,
    story_plan: Dict[str, int],
) -> str:
    cleaned = str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    # Remove obvious scene/shot labels while keeping following story content.
    cleaned = re.sub(
        r"(?im)^\s*(scene\s*\d+\s*[:：]|[\[【（(]?\s*(画面|分镜)\s*[一二三四五六七八九十\d]+\s*[\]】）)]?\s*[:：]?)\s*",
        "",
        cleaned,
    )

    # Remove speaker labels such as “小鼹鼠：” or “妈妈:”, but keep dialogue text.
    cleaned = re.sub(r"(?m)^\s*[^\n：:]{1,12}\s*[:：]\s*", "", cleaned)

    # Remove polluted Latin words and common broken tokens.
    cleaned = re.sub(r"(?i)\b(mexico|whatsapp|undefined|null|nan|user|assistant|system|role)\b", "", cleaned)
    cleaned = cleaned.replace("小ěr", "").replace("小er", "").replace("xiaoer", "")
    cleaned = cleaned.replace('"', "")
    cleaned = cleaned.replace("“", "").replace("”", "")
    cleaned = cleaned.replace("�", "")

    # Remove dangling dialogue questions and dialogue fragments that often remain after LLM repair.
    cleaned = re.sub(
        r"[^。！？!?]{0,50}(你能帮我吗|可以帮我吗|要帮我吗|你能带上我吗|能带上我吗)[^。！？!?]*[？?]",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"[^。！？!?]{0,40}说[:：]",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"谢谢你的夸奖[^。！？!?]*[。！？!?]?",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"[^。！？!?]{0,30}(哇|呀|啊)[！!][^。！？!?]{0,30}[。！？!?]?",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"[^。！？!?]{0,30}(你真勇敢|我一定要|我不会|我还有很多要学|当然可以|太好了|我也想看看|我要去摘松果)[^。！？!?]{0,30}[。！？!?]?",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"[^。！？!?]{0,30}(我们想带你去我们家|带你去我们家|看看我们画的画)[^。！？!?]{0,40}[。！？!?]?",
        "",
        cleaned,
    )

    # Normalize punctuation and obvious duplicated characters/fragments.
    replacements = {
        "，，，": "，",
        "，，": "，",
        "。。。": "。",
        "。。": "。",
        "！！": "！",
        "？？": "？",
        "、、": "、",
        "的的": "的",
        "地地": "地",
        "了了": "了",
        "在在": "在",
        "着着": "着",
        "再再": "再",
        "它它": "它",
        "小小鼹鼠": "小鼹鼠",
        "雪里": "雪人",
        "铲铲": "小铲子",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)

    lines = []
    for line in cleaned.split("\n"):
        item = " ".join(str(line or "").split()).strip()
        if not item:
            continue
        lines.append(item)

    cleaned = "".join(lines).strip()

    # Length-based truncation policy.
    #
    # Previous policy: any story exceeding target_max was sentence-trimmed
    # from the BEGINNING — append sentences until the next one would
    # overshoot, then drop everything after. That destroyed the story's
    # ending (climax + resolution), producing the "戛然而止" failure
    # users reported on 5–15% of generations.
    #
    # New policy:
    #   1) Below `hard_threshold` (= duration × 5 chars/sec × 1.5): do NOT
    #      truncate. The TTS global speedup pass (capped at 1.5×) is
    #      enough to bring the audio back to target duration without
    #      cutting any narrative content. The story's complete arc is
    #      preserved.
    #   2) Above `hard_threshold`: even maxed-out TTS speedup can't
    #      compress the audio to target — we have to drop some content.
    #      Drop the MIDDLE (~15% of sentences) rather than the ENDING,
    #      so the surviving arc still reads as setup → (compressed
    #      development) → climax → resolution.
    target_max = int(story_plan.get("target_max_chars") or 0)
    target_min = int(story_plan.get("target_min_chars") or 0)
    target_chars = int(story_plan.get("target_chars") or 0)
    duration_sec = int(story_plan.get("duration_sec") or 0)

    # 5.0 chars/sec is the calibrated Chinese TTS rate (see runner_story_text
    # comments). 1.5× matches the global speedup cap so we only truncate
    # when speedup alone won't recover the target duration.
    hard_threshold_chars = int(duration_sec * 5.0 * 1.5) if duration_sec > 0 else 0
    current_char_count = runner._story_text_char_count(cleaned)

    if hard_threshold_chars > 0 and current_char_count > hard_threshold_chars:
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[。！？!?])", cleaned)
            if item.strip()
        ]

        # Keep-head-keep-tail only meaningfully helps when there are
        # enough sentences to drop a middle slice without collapsing the
        # narrative. With < 5 sentences we accept the overshoot — the
        # user can regenerate if needed.
        if len(sentences) >= 5:
            head_count = max(1, int(len(sentences) * 0.50))
            tail_count = max(1, int(len(sentences) * 0.35))

            # If head + tail covers (or exceeds) the full list there's
            # no middle to drop. Skip and accept the overshoot.
            if head_count + tail_count < len(sentences):
                kept_sentences = sentences[:head_count] + sentences[-tail_count:]
                repaired = "".join(kept_sentences).strip()

                # Defensive: ensure the surviving last sentence has
                # terminating punctuation. The re.split lookbehind
                # preserves punctuation in each sentence, but a
                # corrupted last sentence could still lack it.
                if repaired and repaired[-1] not in "。！？!?":
                    repaired += "。"

                cleaned = repaired
    # Silence "unused" complaints for variables retained for future tuning.
    _ = (target_max, target_min, target_chars)

    ending_markers = [
        "明白",
        "知道",
        "开心",
        "温暖",
        "勇敢",
        "成长",
        "快乐",
        "再试一次",
        "没有放弃",
        "完成了",
        "成功了",
    ]
    has_warm_ending = any(marker in cleaned[-40:] for marker in ending_markers)

    # Only force-append the canned closing sentence when the story is
    # clearly truncated — i.e. ends WITHOUT proper Chinese punctuation
    # (mid-sentence). Previously this fired whenever the last 40 chars
    # lacked one of a short list of "warmth" keywords, which over-fired
    # on perfectly fine endings ("明天又是新的一天" / "他们慢慢走回家" /
    # etc.) and ended up replacing the LLM's own ending with a generic
    # moral sentence, which then leaked into the user's perceived story
    # quality.
    ends_with_punctuation = bool(cleaned) and cleaned[-1] in "。！？!?"
    needs_forced_closing = bool(cleaned) and not ends_with_punctuation and not has_warm_ending

    if needs_forced_closing:
        closing_sentence = build_story_closing_sentence(topic)
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[。！？!?])", cleaned)
            if item.strip()
        ]

        if sentences:
            narrative_sentences = []
            for sentence in sentences:
                item = sentence.strip()
                if not item:
                    continue
                if item.endswith(("？", "?")):
                    continue
                if "说" in item and ("：" in item or ":" in item):
                    continue
                narrative_sentences.append(item)

            if not narrative_sentences:
                narrative_sentences = sentences

            for keep_count in range(len(narrative_sentences) - 1, 0, -1):
                candidate = "".join(narrative_sentences[:keep_count] + [closing_sentence])
                if (
                    runner._story_text_char_count(candidate) >= max(0, target_min - 10)
                    and runner._story_text_char_count(candidate) <= target_max
                ):
                    cleaned = candidate
                    break
            # If no candidate can satisfy the minimum length, keep the cleaned
            # original text instead of replacing it with only a generic closing
            # sentence. The validator will still reject it as too_short when needed.

    duration_sec = int(story_plan.get("duration_sec") or 0)
    min_tolerance = 10 if duration_sec <= 60 else 20
    effective_target_min = max(0, target_min - min_tolerance)

    if cleaned and runner._story_text_char_count(cleaned) < effective_target_min:
        base = cleaned.rstrip("，、；：")
        if base and not base.endswith(("。", "！", "？")):
            base += "。"

        for sentence in build_story_completion_sentences(topic):
            if sentence in base:
                continue

            candidate = base + sentence
            if target_max <= 0 or runner._story_text_char_count(candidate) <= target_max:
                base = candidate

            if runner._story_text_char_count(base) >= effective_target_min:
                break

        cleaned = base

    if cleaned and not story_text_matches_topic(cleaned, topic):
        anchor_sentence = build_story_topic_anchor_sentence(topic)
        base = cleaned.rstrip("，、；：")
        if base and not base.endswith(("。", "！", "？")):
            base += "。"

        candidate = base + anchor_sentence
        if target_max <= 0 or runner._story_text_char_count(candidate) <= target_max:
            cleaned = candidate
        else:
            sentences = [
                item.strip()
                for item in re.split(r"(?<=[。！？!?])", base)
                if item.strip()
            ]
            for keep_count in range(len(sentences) - 1, 0, -1):
                candidate = "".join(sentences[:keep_count] + [anchor_sentence])
                if (
                    runner._story_text_char_count(candidate) >= effective_target_min
                    and runner._story_text_char_count(candidate) <= target_max
                ):
                    cleaned = candidate
                    break

    return cleaned.strip()


def retry_story_with_llm(
    runner: Any,
    ctx: Any,
    outputs: Dict[str, Any],
    original_text: str,
    invalid_reasons: List[str],
) -> Dict[str, str]:
    _ = outputs

    api_key = runner._llm_api_key()
    if not api_key:
        raise RuntimeError("LLM api key is missing (OPENAI_API_KEY/LLM_API_KEY)")

    model = runner._story_model_name()
    if not model:
        raise RuntimeError("STORY_MODEL/OPENAI_MODEL/LLM_MODEL is missing")

    topic = normalize_story_topic(ctx.input.topic)
    tone_label = runner._tone_label(ctx.input.tone)
    audience_label = runner._audience_label(ctx.input.audience)
    story_plan = runner._duration_story_plan(ctx.input.duration_sec)

    target_min = int(story_plan.get("target_min_chars") or 0)
    target_max = int(story_plan.get("target_max_chars") or 0)
    target_chars = int(story_plan.get("target_chars") or 0)
    retry_target_max = max(target_min, target_max - 30)
    original_char_count = runner._story_text_char_count(original_text)
    retry_mode = evaluate_story_retry_mode(
        original_char_count,
        invalid_reasons,
        story_plan,
    )
    retry_instruction = build_story_retry_instruction(
        retry_mode,
        target_min,
        target_max,
        target_chars,
        retry_target_max,
    )
    reason_text = ", ".join(invalid_reasons)

    system_prompt = (
        "You are a professional children's story editor.\n"
        "Write in Chinese.\n"
        "Return ONLY the revised story text. No JSON, no markdown, no headings."
    )

    user_prompt = (
        f"Topic: {topic}\n"
        f"Tone: {tone_label}\n"
        f"Audience: {audience_label}\n"
        f"Narration pacing target only: about {story_plan['duration_sec']} seconds. Do not mention this duration in the story.\n"
        f"Target Chinese story length: {target_min}-{target_max} Chinese characters, about {target_chars} Chinese characters.\n"
        f"Validation failure reasons: {reason_text}\n"
        f"Original story character count: {original_char_count}\n"
        f"Retry mode: {retry_mode}\n"
        f"Task: {retry_instruction}\n"
        f"Hard constraints:\n"
        f"- Return only clean Chinese story text.\n"
        f"- Do not include JSON, markdown, headings, scene numbers, bullet points, or labels.\n"
        f"- Do not include English/Latin words such as mexico, user, assistant, system, role, undefined, null, nan.\n"
        f"- Do not include scene labels such as Scene 1, Scene 2, or any numbered outline.\n"
        f"- Do not include the selected duration, seconds, target length, or phrases such as 60秒 / 有6秒 in the story.\n"
        f"- Do not include garbled fragments such as 小ěr or repeated corrupted characters.\n"
        f"- Keep the story meaningfully related to the topic.\n"
        f"- Keep a complete beginning, development, problem or discovery, action, resolution, and warm ending.\n"
        f"Original story:\n{original_text.strip()}\n"
    )

    if retry_mode == "light_compress":
        max_tokens = 700
        temperature = 0.4
    elif retry_mode in {"medium_compress", "rewrite_short_complete"}:
        max_tokens = 520
        temperature = 0.3
    elif retry_mode == "rewrite_complete":
        max_tokens = 520
        temperature = 0.3
    else:
        max_tokens = 900
        temperature = 0.5

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    req = urllib_request.Request(
        url=f"{runner._llm_api_base_url().rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=runner._story_timeout_seconds()) as resp:
        raw = resp.read()

    if not raw:
        raise RuntimeError("LLM retry response is empty")

    data = json.loads(raw.decode("utf-8", errors="ignore"))
    content = (
        (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
        or ""
    ).strip()

    if not content:
        raise RuntimeError("LLM retry content is empty")

    parsed = parse_story_payload(content, topic=topic)
    revised_text = parsed["text"] if parsed and parsed.get("text") else content

    return {
        "title": f"{topic}的故事",
        "summary": f"一个围绕“{topic}”展开的短篇故事，整体气质{tone_label}，适合做成{audience_label}向内容。",
        "text": revised_text.strip(),
    }
