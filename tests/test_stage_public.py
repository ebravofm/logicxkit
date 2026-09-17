"""The staging tool's gates, against a bundle from the tracked corpus and a hand-built one: a
title without the neutral prefix is refused, a private word in a note is found, and an autosave
never crosses into the corpus."""

import importlib.util
import plistlib
import tempfile
import unittest
from pathlib import Path

from _paths import REPO

TOOL = REPO / "tools" / "stage_public.py"
if not TOOL.exists():                       # the sdist ships neither the corpus nor its staging tool
    raise unittest.SkipTest(f"no staging tool at {TOOL}")
spec = importlib.util.spec_from_file_location("stage_public", TOOL)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
CORPUS = REPO / "tests" / "corpus"


def _bundle(root: Path, names: dict) -> Path:
    b = root / "x.logicx"
    (b / "Resources").mkdir(parents=True)
    (b / "Resources" / "ProjectInformation.plist").write_bytes(plistlib.dumps({"VariantNames": names}))
    return b


@unittest.skipUnless(CORPUS.is_dir(), "no public corpus")
class TitlesTest(unittest.TestCase):
    def test_every_corpus_bundle_carries_the_neutral_prefix(self):
        bundles = sorted(p for p in CORPUS.glob("*.logicx") if (p / "Resources/ProjectInformation.plist").exists())
        self.assertTrue(bundles)
        for b in bundles:
            with self.subTest(b.name):
                self.assertTrue(stage.titles(b), "the dict of variant names reads as titles")
                self.assertEqual(stage.unneutral(b), [])

    def test_a_title_without_the_prefix_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = _bundle(Path(tmp), {"0": "CLAUDE ok", "1": "My Song"})
            self.assertEqual(stage.unneutral(b), ["My Song"])
            self.assertEqual(stage.unneutral(_bundle(Path(tmp) / "y", {"0": "{PROJECT_NAME}"})), [])


class WordsTest(unittest.TestCase):
    def test_a_private_word_is_found_across_case_and_separators(self):
        self.assertEqual(stage.leaks("the blue-heron take", ["Blue Heron", "other"]), ["Blue Heron"])
        self.assertEqual(stage.leaks("nothing here", ["Blue Heron"]), [])

    def test_autosaves_and_window_images_are_skipped(self):
        skipped = stage.SKIP("x", ["Autosave", "WindowImage_1.jpg", "ProjectData", "DisplayState.plist"])
        self.assertEqual(sorted(skipped), ["Autosave", "WindowImage_1.jpg"])


if __name__ == "__main__":
    unittest.main()
