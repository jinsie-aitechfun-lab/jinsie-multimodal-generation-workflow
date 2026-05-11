from __future__ import annotations

import re
from dataclasses import dataclass, field


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
    return text.strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")


def _cut_at_generic_syntax_boundary(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

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
    value = _clean_piece(piece)
    if not value:
        return ""

    value = _cut_at_generic_syntax_boundary(value)
    if not value:
        return ""

    start = value.find("小")
    if start < 0:
        return ""

    candidate = value[start:].strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")
    if not candidate.startswith("小"):
        return ""

    if len(candidate) >= 5 and candidate[-1] == candidate[-2] and len(candidate) <= 8:
        return candidate

    if len(candidate) <= 4:
        return candidate

    return candidate[:3]


def _extract_open_leading_subject(piece: str) -> str:
    value = _clean_piece(piece)
    if not value:
        return ""

    value = _cut_at_generic_syntax_boundary(value)
    if not value:
        return ""

    first_xiao = value.find("小")
    if first_xiao > 0:
        value = value[:first_xiao]

    match = re.match(r"^([\u4e00-\u9fff]{2,4})", value)
    if not match:
        return ""

    candidate = match.group(1).strip(" \t\n\r，。！？、,.!?：:；;“”\"'《》")

    if len(candidate) == 4:
        candidate = candidate[:3]

    return candidate


def extract_story_subjects(topic: str) -> StorySubjectExtraction:
    clean_topic = normalize_story_topic(topic)

    pieces = re.split(r"(?:、|，|,|和|跟|与|及|同|还有|以及)", clean_topic)

    subjects: list[str] = []

    leading_subject = _extract_open_leading_subject(clean_topic)
    if leading_subject:
        subjects.append(leading_subject)

    for piece in pieces:
        subject = _extract_open_xiao_subject(piece)
        if not subject:
            continue
        if subject not in subjects:
            subjects.append(subject)

    if not subjects:
        fallback = _extract_open_xiao_subject(clean_topic)
        if fallback:
            subjects.append(fallback)

    if not subjects:
        fallback = _extract_open_leading_subject(clean_topic)
        if fallback:
            subjects.append(fallback)

    if not subjects:
        return StorySubjectExtraction()

    return StorySubjectExtraction(
        primary_subject=subjects[0],
        supporting_subjects=subjects[1:],
    )


def story_main_subject(topic: str) -> str:
    extracted = extract_story_subjects(topic)
    return extracted.primary_subject or "主角"
