from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class GeneratedAssetCacheContractTests(unittest.TestCase):
    def test_only_stably_versioned_generated_images_are_immutable(self):
        source = (ROOT / "app/services/cache_control_static.py").read_text(
            encoding="utf-8"
        )
        immutable_branch = source.split("is_versioned_generated_image =", 1)[1]
        self.assertIn('path.startswith("mock/image/")', immutable_branch)
        self.assertIn('bool(query.get("v", [""])[0])', immutable_branch)
        self.assertIn('path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))', immutable_branch)
        self.assertIn('"public, max-age=31536000, immutable"', immutable_branch)

    def test_unversioned_assets_outputs_and_api_responses_are_not_immutable(self):
        source = (ROOT / "app/services/cache_control_static.py").read_text(
            encoding="utf-8"
        )
        main = (ROOT / "app/main.py").read_text(encoding="utf-8")
        self.assertIn('else "public, max-age=0, must-revalidate"', source)
        self.assertIn('RevalidatingStaticFiles(directory=str(ASSETS_DIR))', main)
        self.assertNotIn("outputs.json", source)
        self.assertNotIn("task", source.lower())


if __name__ == "__main__":
    unittest.main()
