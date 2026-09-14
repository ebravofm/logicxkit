"""The packaged templates are exactly the records Logic wrote in the public saves."""

import json
import sys
import unittest
from pathlib import Path

import _goldens

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import regen_data  # noqa: E402


@_goldens.needs("blank-base", "tracks-two-audio-logic")
class ExtractTest(unittest.TestCase):
    def test_the_audio_channel_template_is_logics_new_strip(self):
        t = regen_data.channel(("blank-base", "tracks-two-audio-logic"), "Audio 2")
        self.assertEqual(set(t), {"source", "header", "payload"})
        self.assertEqual(bytes.fromhex(t["header"])[:4], b"OCuA")
        self.assertGreater(len(bytes.fromhex(t["payload"])), 200)      # a mixer record, not a stub


class PackagedMatchesCorpusTest(unittest.TestCase):
    def test_every_packaged_file_matches_a_fresh_extraction(self):
        for name, (keys, make) in regen_data.TEMPLATES.items():
            with self.subTest(name):
                missing = [k for k in keys if _goldens.path(k) is None]
                if missing:
                    self.skipTest(f"golden(s) not on this machine: {', '.join(missing)}")
                packaged = json.loads((regen_data.OUT / "logic" / name).read_text())
                self.assertEqual(packaged, make())


if __name__ == "__main__":
    unittest.main()
