from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from PIL import ImageFont


DEFAULT_VIDEO_WIDTH = 1280
DEFAULT_VIDEO_HEIGHT = 720
SUBTITLE_SAFE_WIDTH_RATIO = 0.84
SUBTITLE_FONT_SIZE_RATIO = 42 / DEFAULT_VIDEO_HEIGHT
SUBTITLE_MARGIN_V_RATIO = 46 / DEFAULT_VIDEO_HEIGHT
SUBTITLE_FONT_NAME = "Noto Sans CJK SC"
LIBASS_SRT_PLAY_RES_X = 384
LIBASS_SRT_PLAY_RES_Y = 288

_BREAK_AFTER = frozenset("，。、；？！,.!?;:")
_CLOSING_PUNCTUATION = frozenset("，。；？！、,.!?;:）】》」』”’")
_TOKEN_RE = re.compile(
    r"[A-Za-z0-9]+(?:['’._/+:-][A-Za-z0-9]+)*|[ \t]+|.",
    re.DOTALL,
)


@dataclass(frozen=True)
class SubtitleLayout:
    video_width: int
    video_height: int
    max_text_width: float
    font_size: int
    margin_l: int
    margin_r: int
    margin_v: int
    ass_font_size: int
    ass_margin_l: int
    ass_margin_r: int
    ass_margin_v: int
    font_name: str
    font_path: Path


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def infer_video_dimensions(image_assets: Dict[str, Any]) -> Tuple[int, int]:
    assets = image_assets.get("assets") or []
    if not isinstance(assets, list):
        return DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        refs: Iterable[Dict[str, Any]] = (
            asset.get("selected_asset_ref") or {},
            asset,
        )
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            width = _positive_int(ref.get("width"))
            height = _positive_int(ref.get("height"))
            if width and height:
                return width, height

    return DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT


@lru_cache(maxsize=1)
def resolve_subtitle_font() -> Tuple[Path, str]:
    candidates = (
        (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            SUBTITLE_FONT_NAME,
        ),
        (Path("/System/Library/Fonts/PingFang.ttc"), "PingFang SC"),
        (Path("/Library/Fonts/Arial Unicode.ttf"), "Arial Unicode MS"),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            "DejaVu Sans",
        ),
    )
    for path, family in candidates:
        if path.is_file():
            return path, family
    raise RuntimeError(
        "No supported subtitle font found. Install fonts-noto-cjk in the runtime."
    )


def build_subtitle_layout(
    video_width: int = DEFAULT_VIDEO_WIDTH,
    video_height: int = DEFAULT_VIDEO_HEIGHT,
) -> SubtitleLayout:
    width = _positive_int(video_width) or DEFAULT_VIDEO_WIDTH
    height = _positive_int(video_height) or DEFAULT_VIDEO_HEIGHT
    font_path, font_name = resolve_subtitle_font()
    margin_l = max(16, int(round(width * (1 - SUBTITLE_SAFE_WIDTH_RATIO) / 2)))
    margin_r = margin_l
    font_size = max(24, int(round(height * SUBTITLE_FONT_SIZE_RATIO)))
    margin_v = max(24, int(round(height * SUBTITLE_MARGIN_V_RATIO)))
    ass_font_size = max(
        8,
        int(round(font_size * LIBASS_SRT_PLAY_RES_Y / height)),
    )
    ass_margin_l = max(
        1,
        int(round(margin_l * LIBASS_SRT_PLAY_RES_X / width)),
    )
    ass_margin_r = max(
        1,
        int(round(margin_r * LIBASS_SRT_PLAY_RES_X / width)),
    )
    ass_margin_v = max(
        1,
        int(round(margin_v * LIBASS_SRT_PLAY_RES_Y / height)),
    )
    return SubtitleLayout(
        video_width=width,
        video_height=height,
        max_text_width=float(width - margin_l - margin_r),
        font_size=font_size,
        margin_l=margin_l,
        margin_r=margin_r,
        margin_v=margin_v,
        ass_font_size=ass_font_size,
        ass_margin_l=ass_margin_l,
        ass_margin_r=ass_margin_r,
        ass_margin_v=ass_margin_v,
        font_name=font_name,
        font_path=font_path,
    )


def _trim_tokens(tokens: Sequence[str]) -> List[str]:
    trimmed = list(tokens)
    while trimmed and trimmed[0].isspace():
        trimmed.pop(0)
    while trimmed and trimmed[-1].isspace():
        trimmed.pop()
    return trimmed


def _tokens_text(tokens: Sequence[str]) -> str:
    return "".join(tokens).strip()


def _preferred_break_index(
    tokens: Sequence[str],
    *,
    font: ImageFont.FreeTypeFont,
    minimum_width: float,
) -> int:
    for index in range(len(tokens) - 1, -1, -1):
        if tokens[index] not in _BREAK_AFTER:
            continue
        prefix = _tokens_text(tokens[: index + 1])
        if prefix and font.getlength(prefix) >= minimum_width:
            return index + 1
    return 0


def wrap_subtitle_lines(text: str, layout: SubtitleLayout) -> List[str]:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []

    font = ImageFont.truetype(str(layout.font_path), layout.font_size)
    tokens = _TOKEN_RE.findall(normalized)
    lines: List[str] = []
    current: List[str] = []

    for token in tokens:
        if token.isspace() and not current:
            continue

        candidate = _tokens_text([*current, token])
        if not current or font.getlength(candidate) <= layout.max_text_width:
            current.append(token)
            continue

        if token in _CLOSING_PUNCTUATION and len(current) > 1:
            moved = current[-1]
            prefix = _tokens_text(current[:-1])
            suffix = _tokens_text([moved, token])
            if (
                prefix
                and font.getlength(prefix) <= layout.max_text_width
                and font.getlength(suffix) <= layout.max_text_width
            ):
                lines.append(prefix)
                current = [moved, token]
                continue

        break_index = _preferred_break_index(
            current,
            font=font,
            minimum_width=layout.max_text_width * 0.45,
        )
        if break_index:
            prefix = _tokens_text(current[:break_index])
            if prefix:
                lines.append(prefix)
            remainder = current[break_index:]
            preserve_separator = bool(remainder and remainder[-1].isspace())
            current = _trim_tokens(remainder)
            if preserve_separator and current and not token.isspace():
                current.append(" ")
            candidate = _tokens_text([*current, token])
            if not current or font.getlength(candidate) <= layout.max_text_width:
                current.append(token)
                continue

        current_text = _tokens_text(current)
        if current_text:
            lines.append(current_text)
        current = [] if token.isspace() else [token]

    current_text = _tokens_text(current)
    if current_text:
        lines.append(current_text)
    return lines


def layout_subtitle_cues(text: str, layout: SubtitleLayout) -> List[str]:
    lines = wrap_subtitle_lines(text, layout)
    return ["\n".join(lines[index : index + 2]) for index in range(0, len(lines), 2)]


def subtitle_cue_speech_text(cue: str) -> str:
    lines = [line.strip() for line in str(cue or "").splitlines() if line.strip()]
    if not lines:
        return ""

    speech_text = lines[0]
    for line in lines[1:]:
        needs_space = (
            bool(speech_text)
            and speech_text[-1].isascii()
            and line[0].isascii()
            and not speech_text[-1].isspace()
            and not line[0].isspace()
        )
        speech_text += (" " if needs_space else "") + line
    return speech_text


def escape_ffmpeg_filter_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
    )


def build_ffmpeg_subtitle_filter(
    subtitle_path: Path,
    layout: SubtitleLayout,
) -> str:
    escaped_path = escape_ffmpeg_filter_value(str(subtitle_path))
    escaped_fonts_dir = escape_ffmpeg_filter_value(str(layout.font_path.parent))
    style = ",".join(
        (
            f"FontName={layout.font_name}",
            f"FontSize={layout.ass_font_size}",
            "Alignment=2",
            f"MarginL={layout.ass_margin_l}",
            f"MarginR={layout.ass_margin_r}",
            f"MarginV={layout.ass_margin_v}",
            "WrapStyle=2",
            "Outline=2",
            "Shadow=0",
        )
    )
    return (
        f"subtitles=filename='{escaped_path}'"
        f":original_size={layout.video_width}x{layout.video_height}"
        f":fontsdir='{escaped_fonts_dir}'"
        f":force_style='{style}'"
    )
