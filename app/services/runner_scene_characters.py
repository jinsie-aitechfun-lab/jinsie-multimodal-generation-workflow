from __future__ import annotations

from typing import Any, Dict, List, Optional


class RunnerSceneCharactersSupport:
    """Scene-level character binding and prompt-contract helpers.

    Extracted as Step 6 of the runner refactor. These helpers bridge the
    global character manifest and per-scene character bindings used by
    storyboard, image prompts, and image asset metadata. They are pure
    dict/list transformations and intentionally avoid IO or provider calls.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def _character_label(self, item: Dict[str, Any]) -> str:
        return (
            str(item.get("display_name") or "").strip()
            or str(item.get("species") or "").strip()
            or str(item.get("character_id") or "").strip()
        )

    def _character_family(self, item: Dict[str, Any]) -> str:
        text = " ".join(
            [
                str(item.get("display_name") or ""),
                str(item.get("species") or ""),
                str(item.get("visual_identity") or ""),
            ]
        ).lower()

        if any(keyword in text for keyword in ["rabbit", "bunny", "兔"]):
            return "rabbit"
        if any(keyword in text for keyword in ["turtle", "tortoise", "乌龟", "海龟", "龟"]):
            return "turtle"
        return ""

    def _family_forbidden_traits(self, family: str) -> List[str]:
        if family == "rabbit":
            return [
                "no rabbit ears",
                "no bunny ears",
                "no long upright rabbit ears",
                "no external ears",
                "no fluffy rabbit tail",
                "no rabbit body",
            ]
        if family == "turtle":
            return [
                "no turtle shell",
                "no hard turtle shell",
                "no shell on body",
                "no turtle body",
                "no short turtle legs",
            ]
        return []

    def _cross_character_forbidden_traits(
        self,
        character: Dict[str, Any],
        scene_characters: List[Dict[str, Any]],
    ) -> List[str]:
        character_family = self._character_family(character)
        if not character_family:
            return []

        other_families: List[str] = []
        for other in scene_characters:
            if not isinstance(other, dict):
                continue

            other_label = self._character_label(other)
            character_label = self._character_label(character)
            if other_label and other_label == character_label:
                continue

            other_family = self._character_family(other)
            if (
                other_family
                and other_family != character_family
                and other_family not in other_families
            ):
                other_families.append(other_family)

        constraints: List[str] = []
        seen = set()
        for family in other_families:
            for trait in self._family_forbidden_traits(family):
                if trait and trait not in seen:
                    constraints.append(trait)
                    seen.add(trait)

        return constraints

    def enriched_scene_characters_from_manifest(
        self,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        scene_characters = scene.get("characters") or []
        if not isinstance(scene_characters, list):
            return []

        manifest_items = self._runner._character_manifest_support.character_manifest_items(
            outputs
        )
        manifest_by_id: Dict[str, Dict[str, Any]] = {}
        manifest_by_name: Dict[str, Dict[str, Any]] = {}

        for item in manifest_items:
            if not isinstance(item, dict):
                continue

            character_id = str(item.get("character_id") or "").strip()
            display_name = str(item.get("display_name") or "").strip()
            species = str(item.get("species") or "").strip()

            if character_id:
                manifest_by_id[character_id] = item
            for key in [display_name, species]:
                if key:
                    manifest_by_name[key] = item

        enriched: List[Dict[str, Any]] = []

        for binding in scene_characters:
            if not isinstance(binding, dict):
                continue

            character_id = str(binding.get("character_id") or "").strip()
            display_name = str(binding.get("display_name") or "").strip()
            species = str(binding.get("species") or "").strip()

            manifest_item = (
                manifest_by_id.get(character_id)
                or manifest_by_name.get(display_name)
                or manifest_by_name.get(species)
            )

            if manifest_item:
                enriched.append(
                    {
                        **dict(binding),
                        **dict(manifest_item),
                    }
                )
            else:
                enriched.append(dict(binding))

        return enriched

    def scene_character_bindings(
        self, outputs: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        bindings: List[Dict[str, Any]] = []
        for item in self._runner._character_manifest_support.character_manifest_items(
            outputs
        ):
            bindings.append(
                {
                    "character_id": item.get("character_id"),
                    "display_name": item.get("display_name"),
                    "species": item.get("species"),
                    "role_type": item.get("role_type"),
                }
            )
        return bindings

    def manifest_character_by_id(
        self,
        outputs: Dict[str, Any],
        character_id: str,
    ) -> Optional[Dict[str, Any]]:
        target = str(character_id or "").strip()
        if not target:
            return None

        for item in self._runner._character_manifest_support.character_manifest_items(
            outputs
        ):
            if str(item.get("character_id") or "").strip() == target:
                return item
        return None

    def scene_character_required_presence_block(
        self,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
    ) -> str:
        scene_characters = scene.get("characters") or []
        if not isinstance(scene_characters, list) or len(scene_characters) < 2:
            return ""

        required_names: List[str] = []
        primary_names: List[str] = []
        secondary_names: List[str] = []

        for binding in scene_characters:
            if not isinstance(binding, dict):
                continue

            character_id = str(binding.get("character_id") or "").strip()
            manifest_item = self.manifest_character_by_id(outputs, character_id)
            if manifest_item is None:
                continue

            display_name = str(manifest_item.get("display_name") or "").strip()
            species = str(manifest_item.get("species") or "").strip()
            role_type = str(manifest_item.get("role_type") or "").strip()

            name = display_name or species
            if not name:
                continue

            if name not in required_names:
                required_names.append(name)

            if role_type == "primary":
                if name not in primary_names:
                    primary_names.append(name)
            else:
                if name not in secondary_names:
                    secondary_names.append(name)

        if len(required_names) < 2:
            return ""

        required_text = " and ".join(required_names)
        primary_text = (
            " and ".join(primary_names) if primary_names else required_names[0]
        )
        secondary_text = " and ".join(secondary_names)

        parts = [
            f"required scene characters: {required_text}",
            f"first priority: draw a multi-character scene with {required_text}, not a solo portrait",
            f"hard requirement: include all of {required_text} together in the same image",
            f"hard requirement: {required_text} must all be clearly visible at the same time in one coherent composition",
            "every listed scene character must be a real on-screen character in the frame, not omitted, not hidden, not cropped out, and not reduced to a tiny background decoration",
            "do not render only one character when multiple required scene characters are listed",
            "do not omit any listed scene character",
            "do not merge multiple characters into one body",
            "do not create a hybrid creature that combines traits from multiple required characters",
            "do not replace one character with another character",
            "anatomy separation: only rabbit characters may have long upright ears; only turtle characters may have shells",
            "turtle anatomy rule: turtles must have an earless rounded reptile head with no external ears",
            "rabbit anatomy rule: rabbits must not have a shell or turtle body",
            "give every required character clear readable scale and enough visual space",
            f"{primary_text} may lead the action, but must not hide, replace, or visually erase the other required characters",
        ]

        if secondary_text:
            parts.append(
                f"{secondary_text} must be clearly visible near {primary_text} and are not optional background hints"
            )

        parts.append(
            "if any required scene character is missing, the image is invalid and should be regenerated"
        )

        return "; ".join(parts)

    def scene_character_prompt_block(
        self,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
    ) -> str:
        scene_characters = scene.get("characters") or []
        if not isinstance(scene_characters, list) or not scene_characters:
            return ""

        parts: List[str] = []
        required_names: List[str] = []
        enriched_scene_characters = self.enriched_scene_characters_from_manifest(
            outputs,
            scene,
        )

        for binding in scene_characters:
            if not isinstance(binding, dict):
                continue

            character_id = str(binding.get("character_id") or "").strip()
            manifest_item = self.manifest_character_by_id(outputs, character_id)
            if manifest_item is None:
                continue

            display_name = str(manifest_item.get("display_name") or "").strip()
            species = str(manifest_item.get("species") or "").strip()
            role_type = str(manifest_item.get("role_type") or "").strip()

            signature_traits = manifest_item.get("signature_traits") or []
            forbidden_traits = manifest_item.get("forbidden_traits") or []
            cross_forbidden_traits = self._cross_character_forbidden_traits(
                manifest_item,
                enriched_scene_characters,
            )

            name = display_name or species
            if name and name not in required_names:
                required_names.append(name)

            signature_text = ", ".join(
                item.strip() for item in signature_traits if str(item).strip()
            )
            forbidden_text = ", ".join(
                item.strip() for item in forbidden_traits if str(item).strip()
            )
            cross_forbidden_text = ", ".join(
                item.strip()
                for item in cross_forbidden_traits
                if str(item).strip()
            )

            detail_parts = [
                f"{role_type} character",
                f"name: {display_name}" if display_name else "",
                f"species: {species}" if species else "",
                "identity lock: keep exactly the same character design in every scene",
                "appearance lock: keep the same body shape, proportions, facial features, dominant colors, outfit or shell or ears or tail, and the same signature accessory or detail in every scene",
                "consistency rule: do not redesign this character between scenes; only change pose, camera angle, expression, background, and current action",
                "presence rule: when this character is required by the scene, it must appear as a real on-screen character in the frame",
                "strict anatomy rule: do not transfer this character's defining anatomy to any other character",
                f"must keep: {signature_text}" if signature_text else "",
                f"must avoid: {forbidden_text}" if forbidden_text else "",
                f"cross-character must avoid: {cross_forbidden_text}"
                if cross_forbidden_text
                else "",
            ]
            detail_text = "; ".join(part for part in detail_parts if part)
            if detail_text:
                parts.append(detail_text)

        if not parts:
            return ""

        scene_cast_text = ""
        if len(required_names) >= 2:
            scene_cast_text = (
                "scene cast lock: render all required scene characters together in the same frame: "
                + ", ".join(required_names)
            )

        blocks = []
        if scene_cast_text:
            blocks.append(scene_cast_text)
        blocks.append("character definitions: " + " | ".join(parts))
        return " ; ".join(blocks)

    def scene_character_negative_block(
        self,
        outputs: Dict[str, Any],
        scene: Dict[str, Any],
    ) -> str:
        scene_characters = scene.get("characters") or []
        if not isinstance(scene_characters, list) or not scene_characters:
            return ""

        negatives: List[str] = []

        for binding in scene_characters:
            if not isinstance(binding, dict):
                continue

            character_id = str(binding.get("character_id") or "").strip()
            manifest_item = self.manifest_character_by_id(outputs, character_id)
            if manifest_item is None:
                continue

            forbidden_traits = manifest_item.get("forbidden_traits") or []
            for item in forbidden_traits:
                value = str(item or "").strip()
                if value:
                    negatives.append(value)

        enriched_scene_characters = self.enriched_scene_characters_from_manifest(
            outputs,
            scene,
        )
        for character in enriched_scene_characters:
            if not isinstance(character, dict):
                continue

            label = self._character_label(character)
            for item in self._cross_character_forbidden_traits(
                character,
                enriched_scene_characters,
            ):
                value = str(item or "").strip()
                if value:
                    negatives.append(f"{label}: {value}" if label else value)

        generic_negatives = [
            "missing required scene character",
            "character omitted from scene",
            "background-only supporting character",
            "cropped-out supporting character",
            "random color changes for the same character",
            "random character redesign",
            "trait transfer between characters",
            "mixed body parts between characters",
            "merged characters",
            "one character wearing another character's defining body traits",
        ]
        negatives.extend(generic_negatives)

        deduped: List[str] = []
        seen = set()
        for item in negatives:
            if item not in seen:
                deduped.append(item)
                seen.add(item)

        if not deduped:
            return ""

        return "subject negative constraints: " + ", ".join(deduped)

    def character_ids_from_bindings(self, bindings: List[Dict[str, Any]]) -> List[str]:
        results: List[str] = []
        seen = set()

        for item in bindings:
            if not isinstance(item, dict):
                continue
            character_id = str(item.get("character_id") or "").strip()
            if character_id and character_id not in seen:
                results.append(character_id)
                seen.add(character_id)

        return results

    def character_names_from_bindings(self, bindings: List[Dict[str, Any]]) -> List[str]:
        results: List[str] = []
        seen = set()

        for item in bindings:
            if not isinstance(item, dict):
                continue
            name = self._character_label(item)
            if name and name not in seen:
                results.append(name)
                seen.add(name)

        return results
