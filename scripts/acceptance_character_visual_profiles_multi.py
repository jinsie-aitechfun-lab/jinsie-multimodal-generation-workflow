from __future__ import annotations

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


def build_request() -> WorkflowRunRequest:
    return WorkflowRunRequest(
        workflow_id="acceptance_character_visual_profiles_multi",
        session_id="acceptance_character_visual_profiles_multi",
        steps=[
            {"name": "story"},
            {"name": "storyboard"},
            {"name": "image_prompts"},
        ],
        input={
            "topic": "小兔子和小乌龟一起过河",
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
            "structured_characters_enabled": True,
            "characters": [
                {
                    "display_name": "小兔子",
                    "species": "rabbit",
                    "role_type": "primary",
                    "visual_traits": "long upright ears, soft white fur, small red scarf, fluffy round tail",
                    "forbidden_traits": "no turtle shell, no hard round shell, no turtle body, no short turtle legs",
                },
                {
                    "display_name": "小乌龟",
                    "species": "turtle",
                    "role_type": "secondary",
                    "visual_traits": "round green shell, small turtle body, short legs, gentle eyes",
                    "forbidden_traits": "no rabbit ears, no long upright ears, no fluffy rabbit tail, no rabbit body",
                },
            ],
        },
    )


def main() -> int:
    result = WorkflowRunner().run(build_request())
    image_prompts = result.outputs.get("image_prompts") or {}
    payload = image_prompts.get("character_visual_profiles") or {}
    profiles = payload.get("profiles") or []
    prompts = image_prompts.get("prompts") or []
    first_prompt = prompts[0].get("prompt", "") if prompts else ""

    failures: list[str] = []

    print("profile_count =", len(profiles))
    print("payload_count =", payload.get("count"))
    print("has_multi_profile_block =", "multi-character visual profiles" in first_prompt)

    if len(profiles) != 2:
        failures.append(f"expected 2 profiles, got {len(profiles)}")

    by_name = {
        str(item.get("display_name") or "").strip(): item
        for item in profiles
        if isinstance(item, dict)
    }

    for name in ["小兔子", "小乌龟"]:
        profile = by_name.get(name)
        print("---")
        print("name =", name)
        print("profile_exists =", bool(profile))

        if not profile:
            failures.append(f"missing profile for {name}")
            continue

        print("character_id =", profile.get("character_id"))
        print("role_type =", profile.get("role_type"))
        print("profile_source =", profile.get("profile_source"))
        print("character_profile_ready =", profile.get("character_profile_ready"))
        print("visual_identity =", str(profile.get("visual_identity") or "")[:200])
        print("must_keep =", profile.get("must_keep"))
        print("must_avoid =", profile.get("must_avoid"))

        if not profile.get("character_id"):
            failures.append(f"{name}: missing character_id")

        if not profile.get("role_type"):
            failures.append(f"{name}: missing role_type")

        if not profile.get("visual_identity"):
            failures.append(f"{name}: missing visual_identity")

        if not profile.get("must_keep"):
            failures.append(f"{name}: missing must_keep")

        if not profile.get("must_avoid"):
            failures.append(f"{name}: missing must_avoid")

    if "multi-character visual profiles" not in first_prompt:
        failures.append("first prompt missing multi-character visual profiles block")

    for name in ["小兔子", "小乌龟"]:
        if name not in first_prompt:
            failures.append(f"first prompt missing {name}")

    if failures:
        print("---")
        print("SUMMARY = FAIL")
        for failure in failures:
            print("-", failure)
        return 1

    print("---")
    print("SUMMARY = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
