from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple
from urllib import request as urllib_request

from app.services.llm_output_sanitizer import parse_story_payload


def normalize_story_topic(topic: str) -> str:
    value = " ".join(str(topic or "").split()).strip()
    if not value:
        return "一个温暖的童话故事"

    patterns = [
        r"^写一个关于(.+?)的故事$",
        r"^写一篇关于(.+?)的故事$",
        r"^讲一个关于(.+?)的故事$",
        r"^生成一个关于(.+?)的故事$",
    ]
    for pattern in patterns:
        match = re.match(pattern, value)
        if match:
            value = match.group(1).strip()
            break

    value = re.sub(r"^关于", "", value).strip()
    value = re.sub(r"的故事$", "", value).strip()
    return value or "一个温暖的童话故事"


def story_main_subject(topic: str) -> str:
    value = normalize_story_topic(topic)

    for candidate in [
        "小恐龙",
        "小鼹鼠",
        "小兔子",
        "小乌龟",
        "小汽车",
        "小蝌蚪",
        "小机器人",
        "小云朵",
        "小明",
        "公主",
        "超人",
        "孙悟空",
        "奥特曼",
    ]:
        if candidate in value:
            return candidate

    match = re.search(r"(小[\u4e00-\u9fff]{1,4})", value)
    if match:
        return match.group(1)

    animal_match = re.search(
        r"([\u4e00-\u9fff]{1,4}(狗|猫|兔|熊|鸟|龙|鼠|龟|猴|羊|鹿|虎|马|牛))",
        value,
    )
    if animal_match:
        return animal_match.group(1)

    return "主角"


def build_story_closing_sentence(topic: str) -> str:
    clean_topic = normalize_story_topic(topic)
    subject = story_main_subject(clean_topic)

    if "骑自行车" in clean_topic or "自行车" in clean_topic:
        return f"{subject}扶稳车把，心里暖暖的，明白勇敢尝试就会慢慢进步。"

    if "雪人" in clean_topic or "堆雪" in clean_topic:
        return f"{subject}看着雪人，心里暖暖的，明白耐心尝试就会有美好的收获。"

    return f"{subject}心里暖暖的，明白勇敢尝试就会带来美好的收获。"


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
    min_tolerance = 10 if int(story_plan.get("duration_sec") or 0) <= 60 else 20
    effective_target_min = max(0, int(story_plan.get("target_min_chars") or 0) - min_tolerance)
    too_short = story_char_count < effective_target_min
    too_long = (
        int(story_plan.get("duration_sec") or 0) <= 60
        and story_char_count > int(story_plan.get("target_max_chars") or 0)
    )
    has_blocked_tokens = runner._story_text_has_blocked_tokens(cleaned_text)
    has_quality_issues = story_text_has_quality_issues(cleaned_text)

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
        r"[^。！？!?]{0,50}(你能帮我吗|可以帮我吗|要帮我吗)[^。！？!?]*[？?]",
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
        r"[^。！？!?]{0,30}(你真勇敢|我一定要|我不会|我还有很多要学)[^。！？!?]{0,30}[。！？!?]?",
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

    # If it is still too long, keep complete sentences up to the target max.
    target_max = int(story_plan.get("target_max_chars") or 0)
    target_min = int(story_plan.get("target_min_chars") or 0)
    target_chars = int(story_plan.get("target_chars") or 0)

    if target_max > 0 and runner._story_text_char_count(cleaned) > target_max:
        sentences = re.split(r"(?<=[。！？!?])", cleaned)
        selected = []
        for sentence in sentences:
            item = sentence.strip()
            if not item:
                continue
            candidate = "".join(selected) + item
            if runner._story_text_char_count(candidate) > target_max:
                break
            selected.append(item)

        repaired = "".join(selected).strip()

        # If sentence trimming made it too short, keep a tighter character slice
        # and close it with a warm ending.
        if runner._story_text_char_count(repaired) < max(0, target_min - 10):
            repaired = cleaned[: max(target_min, target_chars)].rstrip("，、；：")
            if not repaired.endswith(("。", "！", "？")):
                repaired += "。"

        cleaned = repaired

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

    if cleaned and not has_warm_ending:
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
        f"Selected duration: {story_plan['duration_sec']} seconds\n"
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
