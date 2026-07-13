from __future__ import annotations

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


CASES = [
    {
        "topic": "写一个关于小燕子去旅行的故事",
        "expected_subject": "小燕子",
        "expect_frog_rule": False,
    },
    {
        "topic": "奥特曼打小怪兽",
        "expected_subject": "奥特曼",
        "expect_frog_rule": False,
    },
    {
        "topic": "小蝌蚪找妈妈",
        "expected_subject": "小蝌蚪",
        "expect_frog_rule": True,
    },
    {
        "topic": "孙悟空",
        "expected_subject": "孙悟空",
        "expect_frog_rule": False,
    },
    {
        "topic": "一只会飞的小书包",
        "expected_subject": "一只会飞的小书包",
        "expect_frog_rule": False,
    },
]


def build_request(topic: str) -> WorkflowRunRequest:
    return WorkflowRunRequest(
        workflow_id="acceptance_image_prompt_policy",
        session_id=f"acceptance_image_prompt_policy_{topic[:8]}",
        steps=[
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "image_prompts"},
        ],
        input={
            "topic": topic,
            "duration_sec": 60,
            "audience": "children",
            "tone": "warm",
            "visual_style": "storybook",
            "character_style": "animal",
            "language": "zh",
            "audio_enabled": False,
            "voiceover_enabled": False,
            "subtitle_enabled": True,
            "video_provider": "mock",
            "output_mode": "full_video",
        },
    )


def run_case(runner: WorkflowRunner, case: dict[str, object]) -> bool:
    topic = str(case["topic"])
    expected_subject = str(case["expected_subject"])
    expect_frog_rule = bool(case["expect_frog_rule"])

    result = runner.run(build_request(topic))
    image_prompts = result.outputs.get("image_prompts") or {}
    profile = image_prompts.get("character_visual_profile") or {}
    prompts = image_prompts.get("prompts") or []

    first_prompt = prompts[0].get("prompt", "") if prompts else ""
    subject = profile.get("subject")

    failures: list[str] = []

    if subject != expected_subject:
        failures.append(f"subject mismatch: expected={expected_subject}, actual={subject}")

    if not prompts:
        failures.append("image prompts are empty")

    if "character visual profile" not in first_prompt:
        failures.append("missing character visual profile block")

    if "scene action binding" not in first_prompt:
        failures.append("missing scene action binding block")

    if "subject negative constraints" not in first_prompt:
        failures.append("missing subject negative constraints block")

    has_frog_rule = "frog" in first_prompt.lower()
    if has_frog_rule != expect_frog_rule:
        failures.append(
            f"frog rule mismatch: expected={expect_frog_rule}, actual={has_frog_rule}"
        )

    print(f"\n===== {topic} =====")
    print("profile.subject =", subject)
    print("profile.source =", profile.get("profile_source"))
    print("prompt_count =", len(prompts))
    print("has_visual_profile =", "character visual profile" in first_prompt)
    print("has_scene_action_binding =", "scene action binding" in first_prompt)
    print("has_subject_negative =", "subject negative constraints" in first_prompt)
    print("frog_rule =", has_frog_rule)

    if failures:
        print("FAIL")
        for item in failures:
            print(f"- {item}")
        return False

    print("PASS")
    return True


def main() -> int:
    runner = WorkflowRunner()

    results = [run_case(runner, case) for case in CASES]
    passed = sum(1 for item in results if item)

    print("\n===== summary =====")
    print(f"passed = {passed}/{len(CASES)}")

    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
