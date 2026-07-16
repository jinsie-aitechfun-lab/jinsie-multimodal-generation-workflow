from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import ImageFont

from app.services.runner_audio_render_support import RunnerAudioRenderSupport
from app.services.subtitle_layout import (
    build_ffmpeg_subtitle_filter,
    build_subtitle_layout,
    infer_video_dimensions,
    layout_subtitle_cues,
    subtitle_cue_speech_text,
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

    def test_subtitle_cue_speech_text_preserves_mixed_word_boundaries(self) -> None:
        self.assertEqual(
            "AI Studio 2026继续前进。",
            subtitle_cue_speech_text("AI Studio\n2026继续前进。"),
        )

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


class _FakeAudioRunner:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.tts_calls: list[str] = []
        self.probe_calls: list[Path] = []

    def _ensure_audio_run_dir(self, run_id: str) -> Path:
        path = self.root / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _tts_enabled(self) -> bool:
        return True

    def _tts_fallback_to_mock(self) -> bool:
        return False

    def _tts_provider_name(self) -> str:
        return "fake_tts"

    def _generate_real_tts_audio(
        self,
        *,
        text: str,
        output_path: Path,
        **_kwargs,
    ):
        self.tts_calls.append(text)
        output_path.write_text(text, encoding="utf-8")
        return {
            "provider": "fake_tts",
            "model": "fake",
            "voice": "fake",
            "output_bytes": output_path.stat().st_size,
        }

    def _probe_audio_duration_seconds(self, audio_path: Path) -> float:
        self.probe_calls.append(audio_path)
        text = audio_path.read_text(encoding="utf-8")
        return round(max(0.5, len(text) / 8), 3)

    def _write_audio_directory_manifest(self, run_id, assets):
        return {"run_id": run_id, "asset_count": len(assets)}

    def _group_audio_assets_by_scene(self, assets):
        return [{"scene_id": asset["scene_id"]} for asset in assets]


class SubtitleAudioSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.runner = _FakeAudioRunner(Path(self.temp.name))
        self.support = RunnerAudioRenderSupport(self.runner)
        self.ctx = SimpleNamespace(
            run_id="run_sync",
            input=SimpleNamespace(
                subtitle_enabled=True,
                voice_style="warm",
                duration_sec=60,
            ),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run_case(self, text: str):
        outputs = {
            "story": {"generation_source": "template_fallback"},
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
            "dialogue_script": {
                "enabled": True,
                "lines": [
                    {
                        "line_id": "line_01",
                        "scene_id": "scene_01",
                        "speaker": "narrator",
                        "voice_style": "warm",
                        "text": text,
                    }
                ],
            },
        }
        audio = self.support.run_audio_segments(self.ctx, outputs)
        subtitles = self.support.run_subtitles(
            self.ctx,
            {**outputs, "audio_segments": audio},
        )
        return audio, subtitles

    def assert_audio_and_subtitles_are_one_to_one(self, text: str) -> None:
        audio, subtitles = self._run_case(text)
        audio_items = audio["items"]
        subtitle_items = subtitles["items"]
        self.assertEqual(len(audio_items), len(subtitle_items))
        self.assertEqual(len(audio_items), len(self.runner.tts_calls))
        self.assertEqual(len(audio_items), len(self.runner.probe_calls))
        self.assertEqual(
            "".join(text.split()),
            "".join("".join(item["text"].split()) for item in audio_items),
        )

        current_start = 0.0
        for audio_item, subtitle_item in zip(audio_items, subtitle_items):
            self.assertLessEqual(len(subtitle_item["text"].splitlines()), 2)
            self.assertEqual(current_start, subtitle_item["start_sec"])
            current_start += audio_item["duration_sec"]
            self.assertEqual(current_start, subtitle_item["end_sec"])

    def test_long_chinese_is_split_before_tts(self) -> None:
        text = (
            "清晨的阳光穿过森林，照亮了通往山谷的小路，"
            "孩子们带着地图和勇气出发，寻找传说中的星光湖，"
            "一路上还遇见了许多愿意帮助他们的新朋友。"
        )
        audio, subtitles = self._run_case(text)
        self.assertGreater(len(audio["items"]), 1)
        self.assertEqual(len(audio["items"]), len(subtitles["items"]))

    def test_chinese_without_punctuation_is_split_before_tts(self) -> None:
        self.assert_audio_and_subtitles_are_one_to_one(
            "这是一个没有任何标点但是仍然需要根据真实字体显示宽度提前拆分并分别生成配音的中文字幕同步测试文本"
        )

    def test_mixed_chinese_english_numbers_stays_one_to_one(self) -> None:
        self.assert_audio_and_subtitles_are_one_to_one(
            "AI Studio将在2026年完成Version 2.0升级并支持Cloud Rendering工作流让每一个长字幕块都对应独立配音片段"
        )

    def test_short_text_remains_one_audio_segment_and_one_cue(self) -> None:
        audio, subtitles = self._run_case("故事开始了。")
        self.assertEqual(1, len(audio["items"]))
        self.assertEqual(1, len(subtitles["items"]))

    def test_subtitle_stage_has_no_average_duration_split(self) -> None:
        source = Path(
            "app/services/runner_audio_render_support.py"
        ).read_text(encoding="utf-8")
        subtitle_body = source.split("def run_subtitles", 1)[1].split(
            "def build_video_concat_file", 1
        )[0]
        self.assertNotIn("duration_sec / len(", subtitle_body)
        self.assertNotIn("cue_duration_sec", subtitle_body)


if __name__ == "__main__":
    unittest.main()
