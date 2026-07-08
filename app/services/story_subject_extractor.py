from __future__ import annotations

import re
from dataclasses import dataclass, field

try:
    import jieba.posseg as _posseg
    _JIEBA_AVAILABLE = True
except Exception:  # pragma: no cover
    _JIEBA_AVAILABLE = False


# 量词前缀：一只 / 一辆 / 两头 / 三条 ...
# 这些是角色描述里的计量词，本身不是角色名，抽取时必须跳过。
_MEASURE_NUMERALS = "一二两三四五六七八九十半几多整"
_MEASURE_UNITS = "只头匹条位名个群堆双对朵颗辆棵尾窝口峰羽支张片块"
_LEADING_MEASURE_RE = re.compile(rf"^[{_MEASURE_NUMERALS}]+[{_MEASURE_UNITS}]")

# 指令式开头动词（jieba 不可用时的 fallback）：用于识别 “讲一个…故事 / 写一段…”
# 这类没有真实主角名的前缀，避免把 “讲一 / 写一” 当作主角名。
_INSTRUCTION_LEAD_RE = re.compile(r"^(讲|写|说|编|做|生成|制作|创作|请|帮我|给我|来)")

# 显式命名模式：主角是X / 主人公叫X / 名叫X。这是最可靠的角色名来源。
_INTRO_NAME_RE = re.compile(
    r"(?:主角|主人公|主人翁|主角儿)(?:是|叫做|叫|名叫|为)\s*([\u4e00-\u9fff]{2,5})"
)
_ALSO_NAME_RE = re.compile(r"(?:名叫|叫做)\s*([\u4e00-\u9fff]{2,5})")


def _is_rejected_subject(word: str) -> bool:
    """True 表示这个候选不是有效角色名，应当丢弃。"""
    text = str(word or "").strip()
    if not text:
        return True
    if _LEADING_MEASURE_RE.match(text):  # 一只 / 一辆 ...
        return True
    if len(text) <= 1:
        return True
    if text.endswith(("色", "毛色", "皮肤", "身体", "眼睛")):
        return True
    if _INSTRUCTION_LEAD_RE.match(text):
        return True
    return False


def _looks_like_reduplicated_modifier(text: str) -> bool:
    value = str(text or "").strip()
    return (
        len(value) == 4
        and value[0] == value[1]
        and value[2] == value[3]
    )


def _is_modifier_prefix(text: str) -> bool:
    value = str(text or "").strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")
    if not value:
        return False
    if value.endswith("的"):
        return True
    if value.endswith(("色", "毛色", "皮肤", "身体", "眼睛")):
        return True
    if len(value) <= 2:
        return True
    return _is_rejected_subject(value)


def _strip_trailing_predicate_hint(text: str) -> str:
    value = str(text or "").strip()
    if len(value) > 2 and value[-1] in "着了过":
        return value[:-2].strip()
    if len(value) > 3:
        return value[:-1].strip()
    return value


@dataclass
class StorySubjectExtraction:
    primary_subject: str = ""
    supporting_subjects: list[str] = field(default_factory=list)

    @property
    def all_subjects(self) -> list[str]:
        values: list[str] = []
        if self.primary_subject:
            values.append(self.primary_subject)
        values.extend(self.supporting_subjects)
        return values

    @property
    def is_multi_character(self) -> bool:
        return len(self.all_subjects) > 1


def normalize_story_topic(topic: str) -> str:
    value = " ".join(str(topic or "").split()).strip()
    if not value:
        return "一个温暖的童话故事"

    wrappers = [
        r"^请帮我写一个关于(.+?)的故事$",
        r"^帮我写一个关于(.+?)的故事$",
        r"^写一个关于(.+?)的故事$",
        r"^写一篇关于(.+?)的故事$",
        r"^讲一个关于(.+?)的故事$",
        r"^生成一个关于(.+?)的故事$",
    ]

    for pattern in wrappers:
        match = re.match(pattern, value)
        if match:
            value = match.group(1).strip()
            break

    value = re.sub(r"^关于", "", value).strip()

    for suffix in ("的故事", "故事", "绘本", "视频", "动画", "短片"):
        if value.endswith(suffix):
            value = value[: -len(suffix)].strip()
            break

    return value.strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》") or "一个温暖的童话故事"


def _clean_piece(value: str) -> str:
    text = str(value or "").strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")
    text = re.sub(r"^(和|跟|与|及|同|还有|以及)", "", text).strip()
    # 去掉开头的量词，例如 “一只圆圆胖胖” → “圆圆胖胖”，避免把量词当角色名。
    text = _LEADING_MEASURE_RE.sub("", text).strip()
    return text.strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")


def _starts_with_verb(text: str) -> bool:
    """True iff jieba's first POS-tagged token is a verb.

    Used to short-circuit subject extraction on *instruction-style*
    topics like "讲一个节奏舒缓的睡前儿童故事..." or "写一个奇幻冒险
    的故事...". Topics that open with a verb have no human-name
    subject in their preamble — any "name" we'd otherwise extract
    (e.g. "讲一", "写一") is a false positive that then flows
    downstream as the protagonist's name, producing nonsense story
    text like "讲一继续认真尝试".

    Returns False when jieba is unavailable (caller proceeds with the
    legacy fallback path), and False on empty / whitespace input.
    """
    if not _JIEBA_AVAILABLE:
        return False
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    tokens = list(_posseg.cut(cleaned))
    if not tokens:
        return False
    return tokens[0].flag.startswith("v")


def _cut_at_verb_boundary_jieba(text: str) -> str:
    """遇到动词或第二个非修饰名词（activity noun）就截断，返回角色名部分。"""
    tokens = list(_posseg.cut(text))
    if len(tokens) <= 1:
        return text  # 单 token，无需截断

    accumulated = ""
    pending_xiao_prefix = False  # 上一个 token 是 "小" 修饰前缀

    for word, flag in tokens:
        # 动词截断
        if flag.startswith("v"):
            break
        # 量词、副词、介词、助词等截断
        if flag in ("m", "d", "p", "u", "e", "y", "o", "w", "f"):
            break

        if flag == "n":
            if pending_xiao_prefix:
                # "小(a)" + "狐狸(n)" → 合并为角色名，继续
                accumulated += word
                pending_xiao_prefix = False
                continue
            if accumulated:
                # 第二个独立名词 → activity noun，截断
                break
            accumulated += word
        elif flag == "a" and word == "小" and not accumulated:
            # "小" 作修饰前缀，暂存，等下一个名词合并
            accumulated += word
            pending_xiao_prefix = True
        elif flag in ("n", "nr", "nz"):
            accumulated += word
            pending_xiao_prefix = False
        else:
            accumulated += word
            pending_xiao_prefix = False

    return accumulated.strip() or text


def _cut_at_generic_syntax_boundary(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    if _JIEBA_AVAILABLE:
        cut = _cut_at_verb_boundary_jieba(text)
        if cut and cut != text:
            return cut

    # fallback: keep only function-word boundaries. Open-class verbs are
    # handled by structural xiao-subject truncation below instead of lists.
    boundaries = ("去", "在", "被", "把", "给", "为", "从", "到", "向", "对", "用")
    best_pos: int | None = None
    for boundary in boundaries:
        pos = text.find(boundary)
        if pos > 0 and (best_pos is None or pos < best_pos):
            best_pos = pos

    if best_pos is not None:
        return text[:best_pos].strip()

    return text


def _extract_open_xiao_subject(piece: str) -> str:
    raw_value = _clean_piece(piece)
    if not raw_value:
        return ""

    start = raw_value.find("小")
    if start < 0:
        return ""

    prefix = raw_value[:start].strip()
    candidate_text = raw_value[start:].strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")

    value = _cut_at_generic_syntax_boundary(candidate_text)
    if not value:
        return ""

    candidate = value.strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")

    if not candidate.startswith("小"):
        return ""

    if not _JIEBA_AVAILABLE and len(candidate) == 4 and candidate[2] != candidate[3]:
        candidate = candidate[:2]
    elif len(candidate) > 4:
        candidate = candidate[:3]

    if prefix and not _is_modifier_prefix(prefix) and len(prefix) <= 2:
        combined = f"{prefix}{candidate}".strip()
        if 2 < len(combined) <= 10 and not _is_rejected_subject(combined):
            return combined

    return "" if _is_rejected_subject(candidate) else candidate


def _extract_open_leading_subject(piece: str) -> str:
    value = _clean_piece(piece)
    if not value:
        return ""

    # BUG-001 fix. Instruction-style topics ("讲一个 X 的故事 / 写一段
    # 关于 Y 的故事") have no real subject name in their preamble; the
    # regex below would blindly grab the first 2–4 chars (e.g. "讲一",
    # "讲一个节") and that fake "name" would flow downstream as the
    # protagonist, producing story text like "讲一继续认真尝试".
    # Short-circuit when jieba reports the very first token is a verb.
    if _starts_with_verb(value) or _INSTRUCTION_LEAD_RE.match(value):
        return ""

    value = _cut_at_generic_syntax_boundary(value)
    if not value:
        return ""

    first_xiao = value.find("小")
    if first_xiao > 0:
        value = value[:first_xiao]
        if len(value) > 3:
            value = value[:-1]

    match = re.match(r"^([\u4e00-\u9fff]{2,4})", value)
    if not match:
        return ""

    candidate = match.group(1).strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")
    if not candidate:
        return ""
    if _is_rejected_subject(candidate):
        return ""
    if _looks_like_reduplicated_modifier(candidate):
        return ""

    if len(candidate) <= 2:
        return candidate

    if len(candidate) >= 3 and candidate[0] == candidate[1]:
        return candidate[:3]

    if len(candidate) == 3:
        return candidate

    return candidate[:2]


def _extract_subjects_from_piece(piece: str) -> list[str]:
    value = _clean_piece(piece)
    if not value:
        return []

    subjects: list[str] = []
    first_xiao = value.find("小")

    if first_xiao > 0:
        prefix = value[:first_xiao].strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")

        if prefix and not _is_modifier_prefix(prefix):
            # 例如“奥特曼打小怪兽”：小 之前是“奥特曼打”，去掉最后的谓词字。
            prefix = _strip_trailing_predicate_hint(prefix)

            leading = _extract_open_leading_subject(prefix)
            if leading:
                subjects.append(leading)

    xiao_subject = _extract_open_xiao_subject(value)
    if xiao_subject:
        subjects.append(xiao_subject)

    if not subjects:
        leading = _extract_open_leading_subject(value)
        if leading:
            subjects.append(leading)

    deduped: list[str] = []
    for subject in subjects:
        if subject and not _is_rejected_subject(subject) and subject not in deduped:
            deduped.append(subject)
    return deduped


def _extract_explicit_named_subjects(text: str) -> list[str]:
    subjects: list[str] = []
    for pattern in (_INTRO_NAME_RE, _ALSO_NAME_RE):
        for match in pattern.finditer(text):
            candidate = _clean_piece(match.group(1))
            candidate = _cut_at_generic_syntax_boundary(candidate)
            if candidate and not _is_rejected_subject(candidate) and candidate not in subjects:
                subjects.append(candidate)
    return subjects

def extract_story_subjects(topic: str) -> StorySubjectExtraction:
    clean_topic = normalize_story_topic(topic)
    explicit_subjects = _extract_explicit_named_subjects(clean_topic)
    if explicit_subjects:
        return StorySubjectExtraction(
            primary_subject=explicit_subjects[0],
            supporting_subjects=explicit_subjects[1:],
        )

    pieces = re.split(r"(?:、|，|,|和|跟|与|及|同|还有|以及)", clean_topic)

    subjects: list[str] = []
    for piece in pieces:
        for subject in _extract_subjects_from_piece(piece):
            if not _is_rejected_subject(subject) and subject not in subjects:
                subjects.append(subject)

    if not subjects:
        for subject in _extract_subjects_from_piece(clean_topic):
            if not _is_rejected_subject(subject) and subject not in subjects:
                subjects.append(subject)

    if not subjects:
        return StorySubjectExtraction()

    return StorySubjectExtraction(
        primary_subject=subjects[0],
        supporting_subjects=subjects[1:],
    )


def story_main_subject(topic: str) -> str:
    extracted = extract_story_subjects(topic)
    return extracted.primary_subject or "主角"
