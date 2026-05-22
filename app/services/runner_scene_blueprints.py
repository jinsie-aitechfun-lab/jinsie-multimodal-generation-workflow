from __future__ import annotations

from typing import Any, Dict, List, Optional


class RunnerSceneBlueprintsSupport:
    """Scene blueprint templates extracted from WorkflowRunner.

    Extracted as Step 10 of the runner refactor. This module owns the
    scene-title, visual-description, shot-type, and transition templates used
    by storyboard generation.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def expand_scene_blueprints(
        self,
        base: List[Dict[str, str]],
        scene_count: int,
    ) -> List[Dict[str, str]]:
        if scene_count <= 0:
            return []
        if not base:
            return []

        expanded: List[Dict[str, str]] = []
        for index in range(scene_count):
            source = base[index % len(base)]
            cycle = index // len(base)
            item = dict(source)
            if cycle > 0:
                item["scene_title"] = (
                    f"{source.get('scene_title', '故事片段')} · 延展 {cycle + 1}"
                )
            expanded.append(item)

        return expanded

    def scene_blueprints(
        self,
        ctx: Any,
        scene_count: int,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        runner = self._runner
        tone_label = runner._tone_label(ctx.input.tone)
        visual_label = runner._visual_style_label(ctx.input.visual_style)
        main_character_display = runner._main_character_display_label(ctx, outputs)
        secondary_character_display = runner._secondary_character_display_label(
            ctx, outputs
        )
        has_secondary_character = runner._has_secondary_character(ctx, outputs)

        if has_secondary_character:
            base = [
                {
                    "scene_title": "故事开场",
                    "visual_description": (
                        f"{visual_label}风格画面，晨光柔和，主角{main_character_display}和朋友{secondary_character_display}第一次一起出场，"
                        f"整体氛围{tone_label}、轻盈而有期待感。"
                    ),
                    "shot_type": "wide",
                    "transition": "fade",
                },
                {
                    "scene_title": "遇到问题",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}停下脚步思考，"
                        f"{secondary_character_display}陪在一旁一起观察环境变化，画面强调困惑与转折。"
                    ),
                    "shot_type": "medium",
                    "transition": "cut",
                },
                {
                    "scene_title": "行动推进",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}与{secondary_character_display}一起尝试解决问题，"
                        f"动作更明确，节奏变得积极，画面更有前进感。"
                    ),
                    "shot_type": "medium",
                    "transition": "dissolve",
                },
                {
                    "scene_title": "温暖收束",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}和{secondary_character_display}完成旅程，表情放松，"
                        f"画面回到温暖明亮的氛围，用来承接结尾情绪。"
                    ),
                    "shot_type": "close-up",
                    "transition": "fade",
                },
                {
                    "scene_title": "回味结尾",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}和{secondary_character_display}回头望向来时的路，"
                        f"环境安静舒展，用于强化余韵与成长感。"
                    ),
                    "shot_type": "wide",
                    "transition": "fade",
                },
                {
                    "scene_title": "片尾定格",
                    "visual_description": (
                        f"{visual_label}风格画面，{main_character_display}和{secondary_character_display}站在新的起点上，"
                        f"适合作为片尾定格镜头，氛围柔和完整。"
                    ),
                    "shot_type": "close-up",
                    "transition": "fade",
                },
            ]
            return self.expand_scene_blueprints(base, scene_count)

        base = [
            {
                "scene_title": "故事开场",
                "visual_description": (
                    f"{visual_label}风格画面，晨光柔和，主角{main_character_display}第一次出场，"
                    f"整体氛围{tone_label}、轻盈而有期待感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "遇到问题",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}停下脚步思考，"
                    f"周围环境出现小小变化，画面强调困惑与转折。"
                ),
                "shot_type": "medium",
                "transition": "cut",
            },
            {
                "scene_title": "行动推进",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}主动尝试解决问题，"
                    f"动作更明确，节奏变得积极，画面更有前进感。"
                ),
                "shot_type": "medium",
                "transition": "dissolve",
            },
            {
                "scene_title": "温暖收束",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}完成旅程，表情放松，"
                    f"画面回到温暖明亮的氛围，用来承接结尾情绪。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
            {
                "scene_title": "回味结尾",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}回头望向来时的路，"
                    f"环境安静舒展，用于强化余韵与成长感。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "片尾定格",
                "visual_description": (
                    f"{visual_label}风格画面，主角{main_character_display}站在新的起点上，"
                    f"适合作为片尾定格镜头，氛围柔和完整。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
        ]
        return self.expand_scene_blueprints(base, scene_count)
