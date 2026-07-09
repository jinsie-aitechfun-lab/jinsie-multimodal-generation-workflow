"""Verify story topic subject extraction fallback cases.

Usage:
    python scripts/verify_story_subject_extractor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.story_subject_extractor import extract_story_subjects, story_main_subject


CASES = [
    ("讲一个节奏舒缓的睡前儿童故事", []),
    ("一只圆圆胖胖的小熊去森林", ["小熊"]),
    ("主角是小米的故事", ["小米"]),
    ("小狗看家", ["小狗"]),
    ("小猫钓鱼", ["小猫"]),
    ("小白兔种萝卜", ["小白兔"]),
    ("灰白小猫和小狗", ["小猫", "小狗"]),
    ("柔和灰白毛色", []),
    ("一只柔和灰白毛色，明亮好奇眼睛", []),
    ("蓝绿色花纹", []),
    ("银色鳞片和蓬松鬃毛", []),
    ("长长耳朵、短短尾巴", []),
    ("一只柔和灰白毛色，明亮好奇眼睛的小灰鼠在月圆之夜冒险", ["小灰鼠"]),
    ("奥特曼打小怪兽", ["奥特曼", "小怪兽"]),
    (
        "讲一个关于勇气的儿童故事。主角是小红，一辆圆圆胖胖、鲜红色车身、"
        "黄色圆圆大灯的可爱小汽车，住在城市边缘的小车库里。",
        ["小红"],
    ),
    (
        "讲一个充满童趣的儿童探险故事。主角是波波，一只圆圆胖胖、银灰色"
        "光滑皮肤、圆圆大眼睛的可爱小海豹。",
        ["波波"],
    ),
    (
        "讲一个关于勇气与成长的儿童故事。主角是阿橙，一只橘红色蓬松毛皮、"
        "白色腹部、金色明亮眼睛的小狐狸。",
        ["阿橙"],
    ),
    (
        "讲一个充满中式童趣的儿童启蒙故事。主角是圆圆，一只黑白相间的"
        "胖嘟嘟大熊猫宝宝，住在江南竹林深处。",
        ["圆圆"],
    ),
]


def main() -> int:
    failures: list[str] = []

    for topic, expected in CASES:
        actual = extract_story_subjects(topic).all_subjects
        if actual != expected:
            failures.append(f"{topic!r}: expected {expected!r}, got {actual!r}")

    if story_main_subject("讲一个节奏舒缓的睡前儿童故事") != "主角":
        failures.append("instruction-style topic should fall back to generic 主角")

    if failures:
        print("SUMMARY = FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: story subject extractor fallback contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
