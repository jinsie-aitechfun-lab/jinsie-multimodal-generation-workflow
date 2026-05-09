from __future__ import annotations

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


def build_request() -> WorkflowRunRequest:
    return WorkflowRunRequest(
        workflow_id="acceptance_image_prompt_multi_character",
        session_id="acceptance_image_prompt_multi_character",
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
    runner = WorkflowRunner()
    result = runner.run(build_request())

    image_prompts = result.outputs.get("image_prompts") or {}
    prompts = image_prompts.get("prompts") or []
    first_prompt = prompts[0].get("prompt", "") if prompts else ""

    checks = {
        "has_prompts": bool(prompts),
        "has_rabbit": "小兔子" in first_prompt,
        "has_turtle": "小乌龟" in first_prompt,
        "rabbit_keep_traits": "long upright ears" in first_prompt and "red scarf" in first_prompt,
        "rabbit_avoid_turtle_traits": "no turtle shell" in first_prompt or "turtle shell" in first_prompt,
        "turtle_keep_traits": "round green shell" in first_prompt and "short legs" in first_prompt,
        "turtle_avoid_rabbit_traits": "no rabbit ears" in first_prompt or "rabbit ears" in first_prompt,
        "has_character_separation": "character separation" in first_prompt,
        "has_no_trait_transfer": "do not transfer visual traits" in first_prompt,
    }

    print("prompt_count =", len(prompts))
    for key, value in checks.items():
        print(f"{key} =", value)

    print("\n--- first prompt preview ---")
    print(first_prompt[:1800])

    failures = [key for key, value in checks.items() if not value]

    if failures:
        print("\nFAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
