from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.services.image_refresh_tasks import ImageRefreshCoordinator
from app.services.runner_image_asset_refs import RunnerImageAssetRefsSupport


class _Review:
    def build_image_review_item_from_asset(self, asset, provider):
        return {
            "scene_id": asset["scene_id"],
            "scene_title": asset["scene_title"],
            "review_status": "auto_selected",
            "selected_asset_ref": asset["selected_asset_ref"],
            "candidate_asset_refs": asset["candidate_asset_refs"],
        }

    def upsert_image_review_item(self, image_review, scene_review_item, provider):
        return {
            **image_review,
            "provider": provider,
            "selected_assets": [scene_review_item],
            "selected_count": 1,
        }


class _Runner:
    def __init__(self):
        self._image_review = _Review()
        self._image_asset_refs = RunnerImageAssetRefsSupport(self)
        self.provider_calls = 0

    def build_image_assets_from_selected_assets(self, *, run_id, image_review, **_kwargs):
        selected = image_review["selected_assets"]
        return {
            "run_id": run_id,
            "status": "completed",
            "assets": [
                {
                    **item["selected_asset_ref"],
                    "scene_id": item["scene_id"],
                    "status": "generated",
                    "selected_asset_ref": item["selected_asset_ref"],
                    "candidate_asset_refs": item["candidate_asset_refs"],
                }
                for item in selected
            ],
        }


def _png_bytes(size=(1280, 720), color=(44, 88, 132, 255)) -> bytes:
    output = io.BytesIO()
    Image.new("RGBA", size, color).save(output, format="PNG")
    return output.getvalue()


class ImageThumbnailTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runner = _Runner()
        self.support = self.runner._image_asset_refs

    def tearDown(self):
        self.temp.cleanup()

    def _ref(self, name="scene_01__candidate_a.png"):
        relative = f"assets/mock/image/run_test/{name}"
        return {
            "scene_id": "scene_01",
            "file_name": name,
            "relative_path": relative,
            "public_url": f"/{relative}",
            "mime_type": "image/png",
        }

    def test_persisted_original_creates_480_by_270_webp_and_metadata(self):
        original = self.root / "scene_01__candidate_a.png"
        ref = self.support.persist_image_asset(original, _png_bytes(), self._ref())
        thumbnail = self.root / "scene_01__candidate_a.thumb.webp"

        self.assertTrue(original.is_file())
        self.assertTrue(thumbnail.is_file())
        with Image.open(thumbnail) as image:
            self.assertEqual("WEBP", image.format)
            self.assertEqual((480, 270), image.size)
        self.assertEqual("/assets/mock/image/run_test/scene_01__candidate_a.thumb.webp", ref["thumbnail_url"])
        self.assertEqual("1280", str(ref["width"]))
        self.assertEqual(720, ref["height"])
        self.assertEqual(480, ref["thumbnail_width"])
        self.assertEqual(270, ref["thumbnail_height"])
        self.assertEqual(str(original.stat().st_mtime_ns), ref["version"])
        self.assertEqual(str(thumbnail.stat().st_mtime_ns), ref["thumbnail_version"])
        self.assertEqual(original.stat().st_size, ref["size_bytes"])
        self.assertEqual(thumbnail.stat().st_size, ref["thumbnail_size_bytes"])

    def test_thumbnail_failure_keeps_stable_original_and_result_ref(self):
        original = self.root / "scene_01__candidate_a.png"
        with patch.object(self.support, "_write_thumbnail_atomic", side_effect=OSError("disk full")):
            ref = self.support.persist_image_asset(original, _png_bytes(), self._ref())

        self.assertTrue(original.is_file())
        self.assertGreater(original.stat().st_size, 0)
        self.assertEqual(str(original.stat().st_mtime_ns), ref["version"])
        self.assertNotIn("thumbnail_url", ref)

    def test_small_source_is_not_upscaled(self):
        original = self.root / "scene_01__candidate_a.png"
        ref = self.support.persist_image_asset(
            original, _png_bytes(size=(320, 180)), self._ref()
        )
        self.assertEqual(320, ref["thumbnail_width"])
        self.assertEqual(180, ref["thumbnail_height"])

    def test_reconcile_backfills_old_candidates_without_provider(self):
        assets_dir = self.root / "assets"
        run_dir = assets_dir / "mock" / "image" / "run_test"
        run_dir.mkdir(parents=True)
        for suffix in ("candidate_a", "candidate_b"):
            (run_dir / f"scene_01__{suffix}.png").write_bytes(_png_bytes())

        workflow_dir = assets_dir / "mock" / "workflow_test"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "outputs.json").write_text(
            json.dumps(
                {
                    "outputs": {
                        "storyboard": {
                            "scenes": [{"scene_id": "scene_01", "scene_title": "Scene 1"}]
                        },
                        "image_review": {"selected_assets": []},
                        "image_assets": {"assets": []},
                    }
                }
            ),
            encoding="utf-8",
        )
        coordinator = ImageRefreshCoordinator(assets_dir, self.runner)
        result = coordinator.reconcile("workflow_test", "run_test", "scene_01")

        self.assertIsNotNone(result)
        self.assertEqual(0, self.runner.provider_calls)
        refs = result["scene_review_item"]["candidate_asset_refs"]
        self.assertEqual(2, len(refs))
        self.assertTrue(all(ref.get("thumbnail_url") for ref in refs))
        self.assertTrue(all(ref.get("thumbnail_version") for ref in refs))
        self.assertIn(
            "thumbnail_url", result["scene_review_item"]["selected_asset_ref"]
        )
        self.assertIn(
            "thumbnail_url", result["image_assets"]["assets"][0]["selected_asset_ref"]
        )
        self.assertEqual(2, len(list(run_dir.glob("*.thumb.webp"))))


if __name__ == "__main__":
    unittest.main()
