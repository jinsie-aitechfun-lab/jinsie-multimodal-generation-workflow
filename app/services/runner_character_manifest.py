from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.schemas.workflow import WorkflowInput


class RunnerCharacterManifestSupport:
    """Character candidate / manifest helpers extracted from WorkflowRunner.

    Extracted as Step 5 of the runner refactor. This module owns the
    data-only character finalization helpers used before story/image
    generation:

    - build_character_candidates
    - build_character_manifest
    - enrich_character_manifest_traits_from_topic
    - apply_visual_profiles_to_character_manifest
    - character_manifest_items / manifest_character_by_role

    The methods stay behavior-compatible with the original runner.py
    implementations and deliberately avoid IO, LLM calls, and async work.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def build_character_candidates(
        self, workflow_input: WorkflowInput
    ) -> List[Dict[str, Any]]:
        if workflow_input.structured_characters_enabled and workflow_input.characters:
            items: List[Dict[str, Any]] = []
            for index, character in enumerate(workflow_input.characters, start=1):
                items.append(
                    {
                        "candidate_id": f"candidate_{index:02d}",
                        "display_name": character.display_name.strip(),
                        "species": character.species.strip(),
                        "role_type": character.role_type,
                        "visual_traits": character.visual_traits.strip(),
                        "forbidden_traits": character.forbidden_traits.strip(),
                        "source": "structured_input",
                    }
                )
            return items

        items: List[Dict[str, Any]] = []

        main_display_name = (
            workflow_input.main_character_display.strip()
            or workflow_input.main_character.strip()
        )
        if main_display_name:
            items.append(
                {
                    "candidate_id": "candidate_01",
                    "display_name": main_display_name,
                    "species": workflow_input.main_character_species.strip() or "None",
                    "role_type": "primary",
                    "visual_traits": workflow_input.main_character_visual_traits.strip(),
                    "forbidden_traits": "",
                    "source": "legacy_main_character",
                }
            )

        secondary_display_name = (
            workflow_input.secondary_character_display.strip()
            or workflow_input.secondary_character.strip()
        )
        if secondary_display_name:
            items.append(
                {
                    "candidate_id": f"candidate_{len(items) + 1:02d}",
                    "display_name": secondary_display_name,
                    "species": workflow_input.secondary_character_species.strip()
                    or "None",
                    "role_type": "secondary",
                    "visual_traits": workflow_input.secondary_character_visual_traits.strip(),
                    "forbidden_traits": "",
                    "source": "legacy_secondary_character",
                }
            )

        return items

    def build_character_manifest(
        self,
        workflow_input: WorkflowInput,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        manifest: List[Dict[str, Any]] = []

        for index, candidate in enumerate(candidates, start=1):
            role_type = str(candidate.get("role_type") or "secondary").strip()
            if role_type == "primary":
                character_id = "char_primary_01"
            else:
                secondary_index = (
                    sum(
                        1
                        for item in manifest
                        if str(item.get("role_type") or "").strip() == "secondary"
                    )
                    + 1
                )
                character_id = f"char_secondary_{secondary_index:02d}"

            visual_traits_text = str(candidate.get("visual_traits") or "").strip()
            forbidden_traits_text = str(candidate.get("forbidden_traits") or "").strip()

            signature_traits = [
                item.strip() for item in visual_traits_text.split(",") if item.strip()
            ]
            forbidden_traits = [
                item.strip()
                for item in forbidden_traits_text.split(",")
                if item.strip()
            ]

            manifest.append(
                {
                    "character_id": character_id,
                    "display_name": str(candidate.get("display_name") or "").strip(),
                    "species": str(candidate.get("species") or "").strip(),
                    "role_type": role_type,
                    "signature_traits": signature_traits,
                    "forbidden_traits": forbidden_traits,
                    "locking_level": "strict",
                    "reference_assets": {
                        "status": "pending",
                        "front_view": None,
                        "side_view": None,
                        "three_quarter_view": None,
                    },
                    "source": str(candidate.get("source") or "").strip(),
                }
            )

        return manifest

    def extract_color_traits_from_topic(self, topic: str) -> List[str]:
        normalized = str(topic or "").strip().lower()
        if not normalized:
            return []

        color_aliases = [
            ("red", ["红色", "红", "red"]),
            ("blue", ["蓝色", "蓝", "blue"]),
            ("green", ["绿色", "绿", "green"]),
            ("yellow", ["黄色", "黄", "yellow"]),
            ("orange", ["橙色", "橙", "orange"]),
            ("pink", ["粉色", "粉", "pink"]),
            ("purple", ["紫色", "紫", "purple"]),
            ("white", ["白色", "白", "white"]),
            ("black", ["黑色", "黑", "black"]),
            ("gray", ["灰色", "灰", "grey", "gray"]),
            ("brown", ["棕色", "棕", "咖啡色", "brown"]),
        ]

        traits: List[str] = []
        for english_color, aliases in color_aliases:
            if any(alias.lower() in normalized for alias in aliases):
                for alias in aliases:
                    if alias not in traits:
                        traits.append(alias)
                if english_color not in traits:
                    traits.append(english_color)

        return traits

    def enrich_character_manifest_traits_from_topic(
        self,
        character_manifest: List[Dict[str, Any]],
        topic: str,
    ) -> List[Dict[str, Any]]:
        color_traits = self.extract_color_traits_from_topic(topic)
        if not color_traits:
            return character_manifest

        enriched_manifest: List[Dict[str, Any]] = []
        for item in character_manifest:
            if not isinstance(item, dict):
                continue

            enriched_item = dict(item)
            signature_traits = list(enriched_item.get("signature_traits") or [])

            for trait in color_traits:
                if trait and trait not in signature_traits:
                    signature_traits.append(trait)

            enriched_item["signature_traits"] = signature_traits
            enriched_manifest.append(enriched_item)

        return enriched_manifest

    def apply_visual_profiles_to_character_manifest(
        self,
        character_manifest: Dict[str, Any],
        character_visual_profiles: Dict[str, Any],
    ) -> Dict[str, Any]:
        characters = character_manifest.get("characters") or []
        profiles = character_visual_profiles.get("profiles") or []

        if not isinstance(characters, list) or not isinstance(profiles, list):
            return character_manifest

        if not characters or not profiles:
            return character_manifest

        def normalize(value: Any) -> str:
            return str(value or "").strip()

        def as_list(value: Any) -> List[str]:
            if isinstance(value, list):
                return [normalize(item) for item in value if normalize(item)]
            if isinstance(value, str):
                return [
                    normalize(item)
                    for item in value.replace("，", ",").replace("；", ",").split(",")
                    if normalize(item)
                ]
            return []

        def extend_unique(base: Any, extra: Any) -> List[str]:
            result: List[str] = []
            seen = set()

            for value in as_list(base) + as_list(extra):
                if value and value not in seen:
                    result.append(value)
                    seen.add(value)

            return result

        profile_by_id: Dict[str, Dict[str, Any]] = {}
        profile_by_name: Dict[str, Dict[str, Any]] = {}

        for profile in profiles:
            if not isinstance(profile, dict):
                continue

            character_id = normalize(profile.get("character_id"))
            display_name = normalize(profile.get("display_name"))
            species = normalize(profile.get("species"))
            subject = normalize(profile.get("subject"))

            if character_id:
                profile_by_id[character_id] = profile

            for key in [display_name, species, subject]:
                if key:
                    profile_by_name[key] = profile

        enriched_characters: List[Dict[str, Any]] = []

        for item in characters:
            if not isinstance(item, dict):
                continue

            character_id = normalize(item.get("character_id"))
            display_name = normalize(item.get("display_name"))
            species = normalize(item.get("species"))

            profile = (
                profile_by_id.get(character_id)
                or profile_by_name.get(display_name)
                or profile_by_name.get(species)
            )

            if not profile:
                enriched_characters.append(dict(item))
                continue

            enriched_item = dict(item)

            enriched_item["signature_traits"] = extend_unique(
                enriched_item.get("signature_traits") or [],
                profile.get("must_keep") or [],
            )
            enriched_item["forbidden_traits"] = extend_unique(
                enriched_item.get("forbidden_traits") or [],
                profile.get("must_avoid") or [],
            )

            for key in [
                "visual_identity",
                "profile_source",
                "profile_generation_source",
                "required_presence_rules",
                "llm_profile_ready",
                "llm_confidence",
            ]:
                value = profile.get(key)
                if value not in (None, "", []):
                    enriched_item[key] = value

            enriched_characters.append(enriched_item)

        return {
            **character_manifest,
            "count": len(enriched_characters),
            "characters": enriched_characters,
        }

    def character_manifest_items(
        self, outputs: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        manifest_output = outputs.get("character_manifest") or {}
        characters = manifest_output.get("characters") or []
        if isinstance(characters, list):
            return characters
        return []

    def manifest_character_by_role(
        self,
        outputs: Dict[str, Any],
        role_type: str,
    ) -> Optional[Dict[str, Any]]:
        for item in self.character_manifest_items(outputs):
            if str(item.get("role_type") or "").strip() == role_type:
                return item
        return None
