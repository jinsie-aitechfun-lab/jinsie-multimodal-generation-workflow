from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


DEFAULT_BASE_URL = "http://127.0.0.1:8004"


@dataclass(frozen=True)
class StoryCase:
    name: str
    topic: str
    expected_title_keywords: tuple[str, ...]
    expected_text_keywords: tuple[str, ...]
    forbidden_keywords: tuple[str, ...] = ()


CASES: tuple[StoryCase, ...] = (
    StoryCase(
        name="mole_snowman",
        topic="小鼹鼠堆雪人",
        expected_title_keywords=("小鼹鼠", "雪人"),
        expected_text_keywords=("小鼹鼠", "雪"),
        forbidden_keywords=("小ěr", "mexico", "Scene", "画面", "分镜", "再再", "它它"),
    ),
    StoryCase(
        name="dinosaur_bicycle",
        topic="写一个关于小恐龙骑自行车的故事",
        expected_title_keywords=("小恐龙", "自行车"),
        expected_text_keywords=("小恐龙", "自行车"),
        forbidden_keywords=("小鼹鼠", "雪人", "小ěr", "mexico", "Scene", "画面", "分镜", "再再", "它它", "写一个关于"),
    ),
    StoryCase(
        name="dog_icecream",
        topic="写一个关于旺旺狗吃雪糕的故事",
        expected_title_keywords=("旺旺狗",),
        expected_text_keywords=("旺旺", "雪糕"),
        forbidden_keywords=("小鼹鼠", "雪人", "小ěr", "mexico", "Scene", "画面", "分镜", "再再", "它它", "主角心里暖暖"),
    ),
    StoryCase(
        name="ultraman_monster",
        topic="奥特曼打小怪兽",
        expected_title_keywords=("奥特曼",),
        expected_text_keywords=("奥特曼",),
        forbidden_keywords=("小鼹鼠", "雪人", "小ěr", "mexico", "Scene", "画面", "分镜", "再再", "它它"),
    ),
    StoryCase(
        name="car_trip",
        topic="小汽车去旅行",
        expected_title_keywords=("小汽车",),
        expected_text_keywords=("小汽车",),
        forbidden_keywords=("小鼹鼠", "雪人", "小ěr", "mexico", "Scene", "画面", "分镜", "再再", "它它"),
    ),
)


def compact_char_count(text: str) -> int:
    return len("".join(str(text or "").split()))


def post_story_case(base_url: str, case: StoryCase, timeout: float) -> dict[str, Any]:
    payload = {
        "workflow_id": f"acceptance_story_{case.name}",
        "session_id": f"acceptance_story_{case.name}_{int(time.time())}",
        "steps": [
            {"name": "story"},
        ],
        "input": {
            "topic": case.topic,
            "duration_sec": 60,
            "audience": "children",
            "tone": "warm",
            "visual_style": "storybook",
            "character_style": "animal",
            "language": "zh",
            "audio_enabled": False,
        },
    }

    req = urllib_request.Request(
        url=f"{base_url.rstrip('/')}/v1/workflow/run",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()

    return json.loads(raw.decode("utf-8"))


def validate_story(case: StoryCase, response: dict[str, Any]) -> list[str]:
    outputs = response.get("outputs") or {}
    story = outputs.get("story") or {}

    title = str(story.get("title") or "")
    text = str(story.get("text") or "")
    generation_source = story.get("generation_source")
    fallback_reason = story.get("fallback_reason")
    char_count = compact_char_count(text)

    failures: list[str] = []

    if generation_source == "template_fallback":
        failures.append("generation_source is template_fallback")

    if fallback_reason not in (None, "", "null"):
        failures.append(f"fallback_reason is not empty: {fallback_reason}")

    if char_count < 170 or char_count > 280:
        failures.append(f"char_count out of range: {char_count}")

    if any(raw in title for raw in ("写一个关于", "生成一个关于", "讲一个关于")):
        failures.append(f"title still contains raw prompt phrase: {title}")

    for keyword in case.expected_title_keywords:
        if keyword not in title:
            failures.append(f"title missing keyword: {keyword}")

    for keyword in case.expected_text_keywords:
        if keyword not in text:
            failures.append(f"text missing keyword: {keyword}")

    for keyword in case.forbidden_keywords:
        if keyword in text or keyword in title:
            failures.append(f"contains forbidden keyword: {keyword}")

    bad_dialogue_fragments = [
        "你能帮我吗",
        "可以帮我吗",
        "要帮我吗",
        "你能带上我吗",
        "当然可以",
        "太好了",
        "我也想看看",
        "谢谢你的夸奖",
    ]
    for fragment in bad_dialogue_fragments:
        if fragment in text:
            failures.append(f"contains bad dialogue fragment: {fragment}")

    if text.endswith(("？", "?", "：", ":")):
        failures.append("text ends with dangling question or label punctuation")

    return failures


def run_case(base_url: str, case: StoryCase, timeout: float, max_attempts: int) -> bool:
    print(f"\n===== case: {case.name} =====")
    print(f"topic: {case.topic}")

    last_failures: list[str] = []

    for attempt in range(1, max_attempts + 1):
        print(f"\n--- attempt {attempt}/{max_attempts} ---")

        try:
            response = post_story_case(base_url, case, timeout)
        except urllib_error.URLError as error:
            print(f"FAIL request_error: {error}")
            return False
        except Exception as error:
            print(f"FAIL unexpected_error: {type(error).__name__}: {error}")
            return False

        story = ((response.get("outputs") or {}).get("story") or {})
        text = str(story.get("text") or "")
        title = story.get("title")
        generation_source = story.get("generation_source")
        fallback_reason = story.get("fallback_reason")
        char_count = compact_char_count(text)

        print(f"title = {title}")
        print(f"generation_source = {generation_source}")
        print(f"fallback_reason = {fallback_reason}")
        print(f"char_count = {char_count}")
        print(f"last_80 = {text[-80:]}")

        failures = validate_story(case, response)
        if not failures:
            print("PASS")
            return True

        last_failures = failures
        print("FAIL")
        for item in failures:
            print(f"- {item}")

    print("\nFINAL FAIL")
    for item in last_failures:
        print(f"- {item}")
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Acceptance checks for story generation retry policy."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Backend base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="HTTP request timeout in seconds.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=1,
        help="Max workflow attempts per case. Use 1 for strict single-run acceptance; increase manually only for LLM sampling observation.",
    )
    parser.add_argument(
        "--case",
        choices=[case.name for case in CASES],
        help="Run only one case.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    selected_cases = CASES
    if args.case:
        selected_cases = tuple(case for case in CASES if case.name == args.case)

    print("Story generation acceptance")
    print(f"base_url = {args.base_url}")
    print(f"cases = {', '.join(case.name for case in selected_cases)}")

    results = [
        run_case(args.base_url, case, args.timeout, args.max_attempts)
        for case in selected_cases
    ]

    passed = sum(1 for item in results if item)
    total = len(results)

    print("\n===== summary =====")
    print(f"passed = {passed}/{total}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
