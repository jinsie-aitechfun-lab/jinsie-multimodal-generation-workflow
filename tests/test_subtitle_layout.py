from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import ImageFont

from app.services.runner_audio_render_support import RunnerAudioRenderSupport
from app.services.subtitle_layout import (
    build_ffmpeg_subtitle_filter,
    build_subtitle_layout,
    infer_video_dimensions,
    layout_subtitle_cues,
    wrap_subtitle_lines,
)


class SubtitleLayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = build_subtitle_layout(1280, 720)
        self.font = ImageFont.truetype(
            str(self.layout.font_path),
            self.layout.font_size,
        )

    def assert_lines_fit(self, text: str) -> None:
        cues = layout_subtitle_cues(text, self.layout)
        self.assertTrue(cues)
        for cue in cues:
            lines = cue.splitlines()
            self.assertLessEqual(len(lines), 2)
            for line in lines:
                self.assertLessEqual(
                    self.font.getlength(line),
                    self.layout.max_text_width,
                )

    def test_long_chinese_prefers_punctuation_and_stays_in_safe_area(self) -> None:
        text = (
            "清晨的阳光穿过森林，照亮了通往山谷的小路，"
            "孩子们带着地图和勇气出发，寻找传说中的星光湖。"
            "他们沿途记录每一处风景，也把新的发现分享给远方的朋友。"
        )
        self.assert_lines_fit(text)
        self.assertGreater(len(wrap_subtitle_lines(text, self.layout)), 2)

    def test_chinese_without_punctuation_wraps_by_measured_width(self) -> None:
        self.assert_lines_fit(
            "这是一个没有任何标点但是仍然需要根据真实字体显示宽度进行安全折行的中文字幕测试"
        )

    def test_mixed_chinese_english_and_numbers(self) -> None:
        text = (
            "AI Studio将在2026年完成Version 2.0升级，"
            "并支持4K视频与Cloud Rendering工作流。"
        )
        self.assert_lines_fit(text)
        rendered = "\n".join(wrap_subtitle_lines(text, self.layout))
        self.assertIn("Cloud Rendering", rendered)
        self.assertIn("Version 2.0", rendered)

    def test_english_does_not_split_words(self) -> None:
        text = (
            "Creative teams can produce consistent animated stories "
            "with reliable subtitle rendering across production environments."
        )
        lines = wrap_subtitle_lines(text, self.layout)
        source_words = text.replace(".", "").split()
        rendered_words = " ".join(lines).replace(".", "").split()
        self.assertEqual(source_words, rendered_words)
        self.assert_lines_fit(text)

    def test_short_subtitle_stays_on_one_line(self) -> None:
        cues = layout_subtitle_cues("故事开始了。", self.layout)
        self.assertEqual(["故事开始了。"], cues)

    def test_two_line_boundary_remains_one_cue(self) -> None:
        text = "欢迎来到星光森林，今天我们一起寻找藏在山谷深处的秘密宝藏。"
        lines = wrap_subtitle_lines(text, self.layout)
        self.assertLessEqual(len(lines), 2)
        self.assertEqual(1, len(layout_subtitle_cues(text, self.layout)))

    def test_dimensions_prefer_selected_asset_ref(self) -> None:
        dimensions = infer_video_dimensions(
            {
                "assets": [
                    {
                        "width": 640,
                        "height": 360,
                        "selected_asset_ref": {"width": 1280, "height": 720},
                    }
                ]
            }
        )
        self.assertEqual((1280, 720), dimensions)

    def test_ffmpeg_filter_pins_font_safe_margins_and_wrapping(self) -> None:
        subtitle_filter = build_ffmpeg_subtitle_filter(
            Path("/tmp/subtitles.srt"),
            self.layout,
        )
        self.assertIn(f"FontName={self.layout.font_name}", subtitle_filter)
        self.assertIn(f"FontSize={self.layout.ass_font_size}", subtitle_filter)
        self.assertIn("Alignment=2", subtitle_filter)
        self.assertIn(f"MarginL={self.layout.ass_margin_l}", subtitle_filter)
        self.assertIn(f"MarginR={self.layout.ass_margin_r}", subtitle_filter)
        self.assertIn(f"MarginV={self.layout.ass_margin_v}", subtitle_filter)
        self.assertIn("WrapStyle=2", subtitle_filter)
        self.assertIn("original_size=1280x720", subtitle_filter)


class RunSubtitlesLayoutTest(unittest.TestCase):
    def test_more_than_two_lines_are_split_into_sequential_cues(self) -> None:
        support = RunnerAudioRenderSupport(SimpleNamespace())
        ctx = SimpleNamespace(input=SimpleNamespace(subtitle_enabled=True))
        outputs = {
            "image_assets": {
                "assets": [
                    {
                        "selected_asset_ref": {
                            "width": 1280,
                            "height": 720,
                        }
                    }
                ]
            },
            "audio_segments": {
                "items": [
                    {
                        "scene_id": "scene_01",
                        "text": (
                            "清晨的阳光穿过森林，照亮了通往山谷的小路，"
                            "孩子们带着地图和勇气出发，寻找传说中的星光湖，"
                            "一路上还遇见了许多愿意帮助他们的新朋友。"
                        ),
                        "duration_sec": 6.0,
                    }
                ]
            },
        }

        result = support.run_subtitles(ctx, outputs)

        self.assertGreater(len(result["items"]), 1)
        self.assertEqual(0.0, result["items"][0]["start_sec"])
        self.assertEqual(6.0, result["items"][-1]["end_sec"])
        for item in result["items"]:
            self.assertLessEqual(len(item["text"].splitlines()), 2)
        self.assertIn("\n", result["srt_preview"])


if __name__ == "__main__":
    unittest.main()
