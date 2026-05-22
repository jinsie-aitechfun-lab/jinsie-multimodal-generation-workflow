from __future__ import annotations

import textwrap
from typing import Any, Dict


class RunnerSceneRenderFallbackSupport:
    """Pure-Python fallback renderer for mock scene PPM frames.

    Extracted as Step 14 of the runner refactor. This module intentionally
    avoids Pillow so mock image generation can still produce a valid frame if
    the primary storybook renderer raises.
    """

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def build_fallback_scene_ppm(
        self,
        *,
        ctx: Any,
        scene: Dict[str, Any],
        index: int,
        theme: Dict[str, Any],
        width: int,
        height: int,
        topic: str,
        scene_title: str,
        body_text: str,
        duration_sec: int,
    ) -> bytes:
        safe_scene_label = f"SCENE {index:02d}"
        safe_footer = f"{index}/{max(1, int(self._runner._scene_count(ctx.input.duration_sec)))}"

        def _ascii_text(value: str, default: str) -> str:
            normalized = "".join(
                ch.upper() if 32 <= ord(ch) <= 126 else " "
                for ch in str(value or "")
            )
            normalized = " ".join(normalized.split())
            return normalized or default

        safe_headline = _ascii_text(scene_title, "STORY FRAME")
        safe_body = _ascii_text(body_text, "WARM STORYBOARD FRAME")
        safe_meta = _ascii_text(
            f"{scene.get('shot_type', 'wide')} {scene.get('transition', 'fade')} {duration_sec}s",
            "WIDE FADE 15S",
        )
        safe_topic = _ascii_text(topic, "STORY VIDEO")

        pixels = bytearray(width * height * 3)

        def _set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
            if x < 0 or y < 0 or x >= width or y >= height:
                return
            i = (y * width + x) * 3
            pixels[i] = color[0]
            pixels[i + 1] = color[1]
            pixels[i + 2] = color[2]

        def _fill_rect(
            x: int, y: int, w: int, h: int, color: tuple[int, int, int]
        ) -> None:
            x0 = max(0, x)
            y0 = max(0, y)
            x1 = min(width, x + w)
            y1 = min(height, y + h)
            for yy in range(y0, y1):
                row = (yy * width + x0) * 3
                for _ in range(x0, x1):
                    pixels[row] = color[0]
                    pixels[row + 1] = color[1]
                    pixels[row + 2] = color[2]
                    row += 3

        def _fill_circle(
            cx: int, cy: int, radius: int, color: tuple[int, int, int]
        ) -> None:
            r2 = radius * radius
            for yy in range(max(0, cy - radius), min(height, cy + radius + 1)):
                for xx in range(max(0, cx - radius), min(width, cx + radius + 1)):
                    dx = xx - cx
                    dy = yy - cy
                    if dx * dx + dy * dy <= r2:
                        _set_pixel(xx, yy, color)

        font = {
            "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
            "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
            "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
            "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
            "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
            "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
            "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
            "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
            "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
            "J": ["00001", "00001", "00001", "00001", "10001", "10001", "01110"],
            "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
            "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
            "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
            "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
            "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
            "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
            "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
            "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
            "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
            "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
            "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
            "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
            "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
            "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
            "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
            "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
            "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
            "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
            "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
            "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
            "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
            "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
            "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
            "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
            "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
            "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
            " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
            "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
            "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
            ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
        }

        def _draw_char(
            x: int, y: int, ch: str, scale: int, color: tuple[int, int, int]
        ) -> int:
            pattern = font.get(ch, font[" "])
            for row_index, row_bits in enumerate(pattern):
                for col_index, bit in enumerate(row_bits):
                    if bit == "1":
                        _fill_rect(
                            x + col_index * scale,
                            y + row_index * scale,
                            scale,
                            scale,
                            color,
                        )
            return 6 * scale

        def _draw_text(
            x: int, y: int, text: str, scale: int, color: tuple[int, int, int]
        ) -> None:
            cursor_x = x
            for ch in text:
                cursor_x += _draw_char(cursor_x, y, ch, scale, color)

        for y in range(height):
            ratio = y / max(1, height - 1)
            r = int(theme["sky_top"][0] * (1 - ratio) + theme["sky_bottom"][0] * ratio)
            g = int(theme["sky_top"][1] * (1 - ratio) + theme["sky_bottom"][1] * ratio)
            b = int(theme["sky_top"][2] * (1 - ratio) + theme["sky_bottom"][2] * ratio)
            _fill_rect(0, y, width, 1, (r, g, b))

        progress_ratio = min(
            1.0,
            max(0.0, index / max(1, int(self._runner._scene_count(ctx.input.duration_sec)))),
        )

        _fill_rect(22, 22, width - 44, 72, theme["accent"])
        _fill_rect(38, 128, 280, height - 182, (255, 255, 255))
        _fill_rect(350, 150, 860, 400, (255, 255, 255))
        _fill_rect(350, 560, 860, 18, (232, 232, 238))
        _fill_rect(350, 560, int(860 * progress_ratio), 18, theme["accent"])

        _fill_circle(136, 242, 66, theme["shape_a"])
        _fill_circle(222, 334, 58, theme["shape_b"])
        _fill_rect(72, 540, 128, 64, theme["shape_c"])

        _draw_text(52, 44, safe_topic[:22], 3, (255, 255, 255))
        _draw_text(72, 420, safe_scene_label, 3, theme["accent"])
        _draw_text(72, 464, safe_meta[:18], 2, theme["text_secondary"])
        _draw_text(392, 192, safe_headline[:24], 3, theme["text_primary"])

        body_lines = textwrap.wrap(safe_body, width=34)[:3]
        if not body_lines:
            body_lines = ["WARM STORYBOARD FRAME"]

        text_y = 276
        for line in body_lines:
            _draw_text(392, text_y, line, 2, theme["text_secondary"])
            text_y += 38

        _draw_text(1100, 528, safe_footer, 2, theme["text_secondary"])

        data = bytearray()
        data.extend(f"P6\n{width} {height}\n255\n".encode("ascii"))
        data.extend(pixels)
        return bytes(data)
