from __future__ import annotations

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


CASES = [
    {
        "topic": "小汽车去旅行",
        "expected_subject": "小汽车",
        "required_terms": ["red", "headlights"],
        "forbidden_identity_terms": [
            "forest path",
            "forest",
            "lake",
            "background",
            "struggling bird",
            "road",
            "river",
        ],
    },
    {
        "topic": "小蝌蚪找妈妈",
        "expected_subject": "小蝌蚪",
        "required_terms": ["tadpole", "tail"],
        "forbidden_identity_terms": [
            "internal organs",
            "transparent body",
            "slightly transparent",
            "adult frog",
            "frog legs",
        ],
        "required_avoid_terms": [
            "frog",
            "adult frog",
            "tadpole replaced by frog",
        ],
        "required_presence_terms": [
            "visible tadpole",
            "do not replace tadpole with frog",
        ],
    },
    {
        "topic": "一只会飞的小书包",
        "expected_subject": "一只会飞的小书包",
        "required_terms": ["backpack", "wings"],
        "forbidden_identity_terms": [
            "flying over",
            "meadow",
            "wildflowers",
            "background",
            "trees",
            "road",
            "river",
        ],
    },
]


def build_request(topic: str) -> WorkflowRunRequest:
    return WorkflowRunRequest(
        workflow_id="acceptance_character_visual_profile_llm",
        session_id=f"acceptance_character_visual_profile_llm_{topic[:8]}",
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


def contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def missing_terms(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() not in lower]


def run_case(runner: WorkflowRunner, case: dict[str, object]) -> bool:
    topic = str(case["topic"])
    expected_subject = str(case["expected_subject"])
    required_terms = list(case.get("required_terms") or [])
    forbidden_identity_terms = list(case.get("forbidden_identity_terms") or [])
    required_avoid_terms = list(case.get("required_avoid_terms") or [])
    required_presence_terms = list(case.get("required_presence_terms") or [])

    result = runner.run(build_request(topic))
    image_prompts = result.outputs.get("image_prompts") or {}
    profile = image_prompts.get("character_visual_profile") or {}
    prompts = image_prompts.get("prompts") or []
    first_prompt = prompts[0].get("prompt", "") if prompts else ""

    subject = str(profile.get("subject") or "")
    source = str(profile.get("profile_source") or "")
    ready = bool(profile.get("llm_profile_ready"))
    visual_identity = str(profile.get("visual_identity") or "")
    must_keep = ", ".join(str(item) for item in (profile.get("must_keep") or []))
    must_avoid = ", ".join(str(item) for item in (profile.get("must_avoid") or []))
    required_presence = ", ".join(
        str(item) for item in (profile.get("required_presence_rules") or [])
    )

    failures: list[str] = []

    if subject != expected_subject:
        failures.append(f"subject mismatch: expected={expected_subject}, actual={subject}")

    if source != "llm_profile":
        failures.append(f"profile source is not llm_profile: {source}")

    if not ready:
        failures.append("llm_profile_ready is not true")

    if len(visual_identity.strip()) < 40:
        failures.append("visual_identity is too short")

    missing_keep = missing_terms(visual_identity + ", " + must_keep, required_terms)
    if missing_keep:
        failures.append(f"missing required visual terms: {missing_keep}")

    if contains_any(visual_identity, forbidden_identity_terms):
        failures.append("visual_identity contains scene-specific leakage")

    missing_avoid = missing_terms(must_avoid, required_avoid_terms)
    if missing_avoid:
        failures.append(f"missing required avoid terms: {missing_avoid}")

    missing_presence = missing_terms(required_presence, required_presence_terms)
    if missing_presence:
        failures.append(f"missing required presence terms: {missing_presence}")

    if "required presence" not in first_prompt:
        failures.append("prompt missing required presence block")

    if "profile source: llm_profile" not in first_prompt:
        failures.append("prompt missing llm profile source block")

    print(f"\n===== {topic} =====")
    print("profile.subject =", subject)
    print("profile.source =", source)
    print("llm_profile_ready =", ready)
    print("visual_identity =", visual_identity)
    print("must_keep =", profile.get("must_keep"))
    print("must_avoid =", profile.get("must_avoid"))
    print("required_presence_rules =", profile.get("required_presence_rules"))
    print("prompt_has_required_presence =", "required presence" in first_prompt)
    print("prompt_has_llm_profile =", "profile source: llm_profile" in first_prompt)

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
