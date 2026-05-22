from __future__ import annotations

from typing import Any, Dict


class RunnerSceneRenderStorybookSupport:
    """Pillow storybook scene renderer for mock image frames.

    Extracted as Step 15 of the runner refactor. The renderer keeps the
    original local Pillow drawing path and delegates exceptional cases to the
    pure-Python fallback renderer.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def build_scene_ppm(
        self, ctx: Any, scene: Dict[str, Any], index: int
    ) -> bytes:
        import io
        import math
        import textwrap
        from pathlib import Path

        width = 1280
        height = 720

        topic = str(getattr(ctx.input, "topic", "") or "Warm Story").strip()
        scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
        scene_title = str(scene.get("scene_title") or f"Scene {index}").strip()
        visual_description = str(scene.get("visual_description", "")).strip()
        narration = str(scene.get("narration", "")).strip()
        duration_sec = int(scene.get("duration_sec") or 0)

        body_text = narration or visual_description or "A warm and gentle story scene."
        body_text = body_text.replace("\n", " ").strip()

        themes = [
            {
                "sky_top": (109, 101, 255),
                "sky_bottom": (243, 236, 255),
                "ground": (236, 226, 220),
                "accent": (120, 104, 255),
                "accent_soft": (224, 218, 255),
                "text_primary": (45, 39, 84),
                "text_secondary": (97, 91, 130),
                "moon": (255, 246, 196),
                "star": (255, 255, 240),
                "cloud": (255, 255, 255),
                "hill": (211, 234, 221),
                "path": (245, 233, 210),
                "bush": (168, 214, 182),
                "shape_a": (255, 210, 218),
                "shape_b": (196, 229, 255),
                "shape_c": (216, 242, 220),
                "rabbit_body": (255, 251, 248),
                "rabbit_ear": (255, 216, 224),
                "rabbit_cloth": (243, 184, 118),
            },
            {
                "sky_top": (255, 188, 134),
                "sky_bottom": (255, 241, 227),
                "ground": (244, 232, 220),
                "accent": (244, 134, 92),
                "accent_soft": (255, 220, 204),
                "text_primary": (94, 57, 38),
                "text_secondary": (138, 99, 80),
                "moon": (255, 243, 201),
                "star": (255, 249, 235),
                "cloud": (255, 255, 255),
                "hill": (219, 233, 205),
                "path": (241, 220, 181),
                "bush": (189, 222, 177),
                "shape_a": (255, 220, 178),
                "shape_b": (255, 203, 213),
                "shape_c": (201, 235, 246),
                "rabbit_body": (255, 251, 248),
                "rabbit_ear": (255, 213, 221),
                "rabbit_cloth": (118, 170, 224),
            },
            {
                "sky_top": (135, 193, 154),
                "sky_bottom": (238, 250, 242),
                "ground": (234, 228, 214),
                "accent": (77, 156, 113),
                "accent_soft": (204, 235, 217),
                "text_primary": (41, 77, 56),
                "text_secondary": (91, 120, 103),
                "moon": (255, 246, 196),
                "star": (255, 255, 240),
                "cloud": (255, 255, 255),
                "hill": (198, 229, 202),
                "path": (237, 220, 186),
                "bush": (147, 202, 157),
                "shape_a": (255, 226, 186),
                "shape_b": (189, 231, 214),
                "shape_c": (207, 216, 245),
                "rabbit_body": (255, 251, 248),
                "rabbit_ear": (255, 216, 224),
                "rabbit_cloth": (135, 164, 245),
            },
        ]
        theme = themes[(max(index, 1) - 1) % len(themes)]

        try:
            from PIL import Image, ImageDraw, ImageFont

            image = Image.new("RGB", (width, height), theme["sky_bottom"])
            draw = ImageDraw.Draw(image)

            font_candidates = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            ]

            def load_font(size: int):
                for p in font_candidates:
                    if Path(p).exists():
                        try:
                            return ImageFont.truetype(p, size=size)
                        except Exception:
                            pass
                return ImageFont.load_default()

            title_font = load_font(36)
            scene_font = load_font(30)
            body_font = load_font(22)
            meta_font = load_font(18)

            def draw_vertical_gradient(y0: int, y1: int, top_color, bottom_color):
                h = max(1, y1 - y0)
                for y in range(y0, y1):
                    ratio = (y - y0) / h
                    r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
                    g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
                    b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))

            def draw_cloud(x: int, y: int, scale: float = 1.0):
                c = theme["cloud"]
                draw.ellipse(
                    (x, y + 16 * scale, x + 90 * scale, y + 74 * scale), fill=c
                )
                draw.ellipse(
                    (x + 42 * scale, y, x + 132 * scale, y + 70 * scale), fill=c
                )
                draw.ellipse(
                    (x + 96 * scale, y + 18 * scale, x + 176 * scale, y + 78 * scale),
                    fill=c,
                )
                draw.rounded_rectangle(
                    (x + 28 * scale, y + 34 * scale, x + 142 * scale, y + 82 * scale),
                    radius=int(18 * scale),
                    fill=c,
                )

            def draw_star(cx: int, cy: int, radius: int):
                points = []
                for i in range(10):
                    angle = math.radians(-90 + i * 36)
                    r = radius if i % 2 == 0 else radius * 0.45
                    points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
                draw.polygon(points, fill=theme["star"])

            def draw_hill(x0: int, y0: int, x1: int, y1: int, color):
                draw.ellipse((x0, y0, x1, y1), fill=color)

            def draw_path(points, color):
                draw.line(points, fill=color, width=34, joint="curve")

            def draw_rabbit(x: int, y: int, scale: float = 1.0, pose: str = "stand"):
                body = theme["rabbit_body"]
                ear = theme["rabbit_ear"]
                cloth = theme["rabbit_cloth"]
                outline = (170, 154, 152)

                draw.ellipse(
                    (x + 18 * scale, y - 44 * scale, x + 42 * scale, y + 28 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )
                draw.ellipse(
                    (x + 48 * scale, y - 52 * scale, x + 72 * scale, y + 24 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )
                draw.ellipse(
                    (x + 25 * scale, y - 32 * scale, x + 35 * scale, y + 16 * scale),
                    fill=ear,
                )
                draw.ellipse(
                    (x + 55 * scale, y - 38 * scale, x + 65 * scale, y + 10 * scale),
                    fill=ear,
                )

                draw.ellipse(
                    (x, y, x + 86 * scale, y + 78 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )

                draw.ellipse(
                    (x + 26 * scale, y + 28 * scale, x + 32 * scale, y + 34 * scale),
                    fill=(68, 58, 58),
                )
                draw.ellipse(
                    (x + 52 * scale, y + 28 * scale, x + 58 * scale, y + 34 * scale),
                    fill=(68, 58, 58),
                )
                draw.ellipse(
                    (x + 38 * scale, y + 40 * scale, x + 48 * scale, y + 48 * scale),
                    fill=(255, 172, 180),
                )
                draw.arc(
                    (x + 32 * scale, y + 44 * scale, x + 54 * scale, y + 58 * scale),
                    start=10,
                    end=170,
                    fill=(120, 104, 110),
                    width=2,
                )

                body_y = y + 62 * scale
                draw.ellipse(
                    (x + 4 * scale, body_y, x + 96 * scale, body_y + 98 * scale),
                    fill=body,
                    outline=outline,
                    width=2,
                )

                draw.rounded_rectangle(
                    (
                        x + 18 * scale,
                        body_y + 30 * scale,
                        x + 82 * scale,
                        body_y + 88 * scale,
                    ),
                    radius=int(18 * scale),
                    fill=cloth,
                )

                draw.line(
                    (
                        x + 18 * scale,
                        body_y + 46 * scale,
                        x - 12 * scale,
                        body_y + 70 * scale,
                    ),
                    fill=outline,
                    width=6,
                )
                draw.line(
                    (
                        x + 80 * scale,
                        body_y + 46 * scale,
                        x + 112 * scale,
                        body_y + 66 * scale,
                    ),
                    fill=outline,
                    width=6,
                )

                if pose == "walk":
                    draw.line(
                        (
                            x + 36 * scale,
                            body_y + 94 * scale,
                            x + 20 * scale,
                            body_y + 134 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )
                    draw.line(
                        (
                            x + 62 * scale,
                            body_y + 94 * scale,
                            x + 78 * scale,
                            body_y + 132 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )
                else:
                    draw.line(
                        (
                            x + 36 * scale,
                            body_y + 94 * scale,
                            x + 30 * scale,
                            body_y + 132 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )
                    draw.line(
                        (
                            x + 62 * scale,
                            body_y + 94 * scale,
                            x + 68 * scale,
                            body_y + 132 * scale,
                        ),
                        fill=outline,
                        width=6,
                    )

                draw.ellipse(
                    (
                        x + 78 * scale,
                        body_y + 52 * scale,
                        x + 100 * scale,
                        body_y + 74 * scale,
                    ),
                    fill=body,
                    outline=outline,
                    width=2,
                )

            def draw_question_mark(x: int, y: int, color):
                draw.arc((x, y, x + 42, y + 42), start=200, end=20, fill=color, width=6)
                draw.line((x + 32, y + 30, x + 24, y + 48), fill=color, width=6)
                draw.ellipse((x + 19, y + 58, x + 27, y + 66), fill=color)

            def draw_arrow(x: int, y: int, color):
                draw.line((x, y, x + 80, y), fill=color, width=10)
                draw.polygon(
                    [(x + 80, y), (x + 52, y - 18), (x + 52, y + 18)], fill=color
                )

            draw_vertical_gradient(
                0, int(height * 0.76), theme["sky_top"], theme["sky_bottom"]
            )
            draw.rectangle((0, int(height * 0.72), width, height), fill=theme["ground"])

            draw_hill(-120, 430, 500, 820, theme["hill"])
            draw_hill(
                330,
                470,
                930,
                860,
                (theme["hill"][0] - 10, theme["hill"][1] - 8, theme["hill"][2] - 6),
            )
            draw_hill(760, 420, 1400, 850, theme["hill"])

            draw_path(
                [(130, 640), (300, 610), (500, 630), (760, 605), (1040, 640)],
                theme["path"],
            )

            moon_x = 980 if index == 1 else 1060 if index == 2 else 930
            moon_y = 84 if index == 1 else 102 if index == 2 else 78
            draw.ellipse(
                (moon_x, moon_y, moon_x + 120, moon_y + 120), fill=theme["moon"]
            )

            for sx, sy, sr in [
                (160, 88, 10),
                (280, 132, 8),
                (860, 62, 9),
                (1180, 180, 7),
                (1020, 236, 6),
            ]:
                draw_star(sx, sy, sr)

            draw_cloud(122, 116, 1.0)
            draw_cloud(708, 148, 0.85)

            if index == 1:
                draw_rabbit(250, 408, scale=1.8, pose="stand")
                draw_cloud(930, 206, 0.72)
                draw.rounded_rectangle(
                    (880, 520, 1160, 590), radius=22, fill=(255, 255, 255)
                )
                draw.text(
                    (910, 542), "晚安，小月亮", font=meta_font, fill=theme["accent"]
                )

            elif index == 2:
                draw_rabbit(200, 424, scale=1.7, pose="stand")
                draw_path(
                    [(480, 638), (610, 586), (740, 612)],
                    (231, 212, 180),
                )
                draw_path(
                    [(610, 586), (720, 522), (850, 510)],
                    (231, 212, 180),
                )
                draw_path(
                    [(610, 586), (724, 654), (860, 674)],
                    (231, 212, 180),
                )
                draw_question_mark(356, 318, theme["accent"])
                draw_question_mark(410, 282, theme["accent_soft"])
                draw.rounded_rectangle(
                    (860, 494, 1170, 594), radius=26, fill=(255, 255, 255)
                )
                draw.text(
                    (895, 520),
                    "要往哪边走呢？",
                    font=body_font,
                    fill=theme["text_primary"],
                )

            else:
                draw_rabbit(286, 420, scale=1.75, pose="walk")
                draw_arrow(804, 478, theme["accent"])
                draw.rounded_rectangle(
                    (934, 394, 1118, 468), radius=26, fill=(255, 255, 255)
                )
                draw.text(
                    (968, 420), "继续向前", font=body_font, fill=theme["text_primary"]
                )
                draw.ellipse(
                    (1032, 520, 1152, 640),
                    fill=(255, 236, 170),
                    outline=(229, 194, 92),
                    width=4,
                )
                draw.ellipse((1066, 552, 1118, 604), fill=(255, 255, 255))
                draw.rounded_rectangle(
                    (1068, 608, 1118, 642), radius=10, fill=(189, 160, 124)
                )

            draw.ellipse((60, 600, 220, 700), fill=theme["bush"])
            draw.ellipse((880, 612, 1080, 712), fill=theme["bush"])
            draw.ellipse(
                (1080, 624, 1230, 714),
                fill=(
                    theme["bush"][0] - 8,
                    theme["bush"][1] - 10,
                    theme["bush"][2] - 6,
                ),
            )

            overlay_x = 42
            overlay_y = 28
            draw.rounded_rectangle(
                (overlay_x, overlay_y, 510, 96), radius=26, fill=(255, 255, 255)
            )
            draw.text(
                (overlay_x + 24, overlay_y + 18),
                topic[:22],
                font=title_font,
                fill=theme["accent"],
            )

            draw.rounded_rectangle((42, 114, 340, 176), radius=20, fill=(255, 255, 255))
            draw.text(
                (64, 128),
                scene_title[:14] if scene_title else f"Scene {index}",
                font=scene_font,
                fill=theme["text_primary"],
            )
            draw.text(
                (250, 132),
                f"{index}/{max(1, int(self._runner._scene_count(ctx.input.duration_sec)))}",
                font=meta_font,
                fill=theme["text_secondary"],
            )

            caption = visual_description or body_text
            caption_lines = textwrap.wrap(caption, width=28)[:2]
            if caption_lines:
                draw.rounded_rectangle(
                    (42, 606, 680, 686), radius=24, fill=(255, 255, 255)
                )
                cy = 622
                for line in caption_lines:
                    draw.text(
                        (66, cy), line, font=body_font, fill=theme["text_secondary"]
                    )
                    cy += 28

            if duration_sec > 0:
                draw.rounded_rectangle(
                    (1090, 620, 1218, 672), radius=18, fill=(255, 255, 255)
                )
                draw.text(
                    (1120, 636),
                    f"{duration_sec}S",
                    font=meta_font,
                    fill=theme["text_secondary"],
                )

            buffer = io.BytesIO()
            image.save(buffer, format="PPM")
            return buffer.getvalue()

        except Exception as e:
            print("[scene_ppm_fallback]", repr(e))
            return self._runner._scene_render_fallback.build_fallback_scene_ppm(
                ctx=ctx,
                scene=scene,
                index=index,
                theme=theme,
                width=width,
                height=height,
                topic=topic,
                scene_title=scene_title,
                body_text=body_text,
                duration_sec=duration_sec,
            )

    def build_scene_png(
        self,
        ctx: Any,
        scene: Dict[str, Any],
        index: int,
    ) -> bytes:
        from io import BytesIO
        from PIL import Image

        ppm_bytes = self.build_scene_ppm(ctx, scene, index)

        input_buffer = BytesIO(ppm_bytes)
        output_buffer = BytesIO()

        image = Image.open(input_buffer)
        image.save(output_buffer, format="PNG")

        return output_buffer.getvalue()
