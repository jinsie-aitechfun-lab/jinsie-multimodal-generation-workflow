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
                        f"{visual_label}风格画面，清晨金色阳光斜射，薄雾弥漫，"
                        f"主角{main_character_display}和朋友{secondary_character_display}在宽阔的起点第一次一起出场，"
                        f"远近景层次丰富，色调明亮金黄，氛围{tone_label}而充满期待。"
                    ),
                    "shot_type": "wide",
                    "transition": "fade",
                },
                {
                    "scene_title": "遇到问题",
                    "visual_description": (
                        f"{visual_label}风格画面，正午明亮直射光，阴影清晰，"
                        f"{main_character_display}在郁郁葱葱的自然环境中停下脚步，"
                        f"{secondary_character_display}陪在一旁观察，近景绿意环绕，色调清新翠绿，强调困惑与转折。"
                    ),
                    "shot_type": "medium",
                    "transition": "cut",
                },
                {
                    "scene_title": "行动推进",
                    "visual_description": (
                        f"{visual_label}风格画面，午后柔和漫射光，云朵飘动，"
                        f"{main_character_display}与{secondary_character_display}在开阔场景中并肩前行，"
                        f"中景俯视视角，天空蓝白色调，画面充满动感。"
                    ),
                    "shot_type": "medium",
                    "transition": "dissolve",
                },
                {
                    "scene_title": "温暖收束",
                    "visual_description": (
                        f"{visual_label}风格画面，夕阳橙红暖光洒落，光晕明显，"
                        f"{main_character_display}和{secondary_character_display}在温馨场所完成旅程，"
                        f"近景双人构图，橙红暖黄色调，氛围温柔满足。"
                    ),
                    "shot_type": "close-up",
                    "transition": "fade",
                },
                {
                    "scene_title": "回味结尾",
                    "visual_description": (
                        f"{visual_label}风格画面，黄昏蓝紫渐变天空，繁星初现，"
                        f"{main_character_display}和{secondary_character_display}在高处回望来时的路，"
                        f"远景广角构图，蓝紫冷暖过渡色调，空间感强，余韵悠长。"
                    ),
                    "shot_type": "wide",
                    "transition": "fade",
                },
                {
                    "scene_title": "片尾定格",
                    "visual_description": (
                        f"{visual_label}风格画面，柔和月光或温暖室内灯光，"
                        f"{main_character_display}和{secondary_character_display}站在新的起点，背景虚化柔美，"
                        f"特写双人肖像，色调柔和梦幻，适合片尾定格。"
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
                    f"{visual_label}风格画面，清晨金色阳光斜射，薄雾弥漫，"
                    f"主角{main_character_display}在宽阔的起点环境第一次出场，"
                    f"远近景层次丰富，整体色调明亮金黄，氛围{tone_label}而充满期待。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "遇到问题",
                "visual_description": (
                    f"{visual_label}风格画面，正午明亮直射光，阴影清晰，"
                    f"主角{main_character_display}在郁郁葱葱的自然环境中停下脚步，"
                    f"近景特写，绿意环绕，画面色调清新翠绿，强调困惑与转折。"
                ),
                "shot_type": "medium",
                "transition": "cut",
            },
            {
                "scene_title": "行动推进",
                "visual_description": (
                    f"{visual_label}风格画面，午后柔和漫射光，云朵飘动，"
                    f"主角{main_character_display}在开阔的场景中奋力前行，"
                    f"中景俯视视角，天空蓝白色调为主，画面充满动感与前进感。"
                ),
                "shot_type": "medium",
                "transition": "dissolve",
            },
            {
                "scene_title": "温暖收束",
                "visual_description": (
                    f"{visual_label}风格画面，夕阳橙红暖光洒落，光晕明显，"
                    f"主角{main_character_display}在温馨的场所完成旅程，表情放松，"
                    f"近景肖像构图，橙红暖黄色调，整体氛围温柔而满足。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
            {
                "scene_title": "回味结尾",
                "visual_description": (
                    f"{visual_label}风格画面，黄昏蓝紫渐变天空，繁星初现，"
                    f"主角{main_character_display}在高处或开阔处回望来时的路，"
                    f"远景广角构图，蓝紫冷暖过渡色调，空间感强，余韵悠长。"
                ),
                "shot_type": "wide",
                "transition": "fade",
            },
            {
                "scene_title": "片尾定格",
                "visual_description": (
                    f"{visual_label}风格画面，柔和月光或温暖室内灯光，"
                    f"主角{main_character_display}站在新的起点，背景虚化柔美，"
                    f"特写肖像镜头，色调柔和梦幻，适合片尾定格。"
                ),
                "shot_type": "close-up",
                "transition": "fade",
            },
        ]
        return self.expand_scene_blueprints(base, scene_count)
