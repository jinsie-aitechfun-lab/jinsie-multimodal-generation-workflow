from __future__ import annotations

from app.schemas.workflow import WorkflowRunRequest
from app.services.runner import WorkflowRunner


def build_request() -> WorkflowRunRequest:
    return WorkflowRunRequest(
        workflow_id="acceptance_scene_character_presence",
        session_id="acceptance_scene_character_presence",
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

    manifest = result.outputs.get("character_manifest") or {}
    characters = manifest.get("characters") or []
    image_prompts = result.outputs.get("image_prompts") or {}
    prompts = image_prompts.get("prompts") or []

    failures: list[str] = []

    if not characters:
        failures.append("character_manifest.characters is empty")

    if not prompts:
        failures.append("image_prompts.prompts is empty")

    required_names = [
        str(item.get("display_name") or "").strip()
        for item in characters
        if str(item.get("display_name") or "").strip()
    ]

    required_traits = []
    for item in characters:
        name = str(item.get("display_name") or "").strip()
        traits = item.get("signature_traits") or []
        forbidden = item.get("forbidden_traits") or []

        for trait in traits:
            value = str(trait or "").strip()
            if value:
                required_traits.append((name, "must_keep", value))

        for trait in forbidden:
            value = str(trait or "").strip()
            if value:
                required_traits.append((name, "must_avoid", value))

    print("manifest_character_count =", len(characters))
    print("prompt_count =", len(prompts))
    print("required_names =", required_names)

    for index, item in enumerate(prompts, start=1):
        scene_id = str(item.get("scene_id") or f"scene_{index:02d}")
        prompt = str(item.get("prompt") or "")

        print("---")
        print("scene_id =", scene_id)
        print("prompt_has_scene_cast_lock =", "scene cast lock" in prompt)
        print("prompt_has_character_definitions =", "character definitions" in prompt)
        print("prompt_has_scene_action_binding =", "scene action binding" in prompt)

        if "scene cast lock" not in prompt:
            failures.append(f"{scene_id}: missing scene cast lock")

        if "character definitions" not in prompt:
            failures.append(f"{scene_id}: missing character definitions")

        if "scene action binding" not in prompt:
            failures.append(f"{scene_id}: missing scene action binding")

        for name in required_names:
            present = name in prompt
            print(f"{scene_id}: has {name} =", present)
            if not present:
                failures.append(f"{scene_id}: missing required character {name}")

        for character_name, trait_type, trait in required_traits:
            present = trait in prompt
            print(f"{scene_id}: has {character_name} {trait_type} {trait} =", present)
            if not present:
                failures.append(
                    f"{scene_id}: missing {character_name} {trait_type} trait: {trait}"
                )

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
