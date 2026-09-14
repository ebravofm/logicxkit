"""The signature track: time signatures, key numbers and bar arithmetic across a change.

The real-file part of tests/logic/test_signature.py; skips without the owner's files."""

import unittest
import _goldens
import _paths
from logicxkit.logic.services.signature import meter, read_signatures
from logicxkit.logicx import project_data

SONGS = sorted(p for d in ("mixes", "legacy") for p in (_paths.RESOURCES / d).glob("*/*.logicx"))
FIVE = _goldens.path("meter-song")
LIST_KEYS = ["signature-list-base-logic", "signature-meter-created-logic", "signature-meter-5-8-bar-6-logic",
             "signature-meter-3-8-bar-6-logic", "signature-key-created-logic", "signature-key-a-minor-logic"]


@unittest.skipUnless(SONGS, "no resources copies")
class GoldenTest(unittest.TestCase):
    def test_every_band_song_is_four_four_in_key_seven(self):
        for song in SONGS:
            times, keys = read_signatures(project_data(song))
            self.assertEqual([(t.tick, t.numerator, t.denominator) for t in times], [(0, 4, 4)], song)
            self.assertEqual([k.number for k in keys], [7], song)

    @unittest.skipUnless(FIVE, "no meter-change golden")
    def test_meter_change_reads_as_the_song_has_it(self):
        data = project_data(FIVE)
        times, _keys = read_signatures(data)
        self.assertEqual([[t.numerator, t.denominator] for t in times], _goldens.fact("meter-song", "meters"))
        self.assertEqual(meter(data).bar(times[1].tick), float(_goldens.fact("meter-song", "change_bar")))


@_goldens.needs(*LIST_KEYS)
class SignatureListTest(unittest.TestCase):
    """Logic's own Signature List creates and edits on the blank project: a meter change on the
    bar line after the playhead, a key change at the playhead, each field one save."""

    def test_each_save_reads_its_events(self):
        for key in LIST_KEYS:
            data = project_data(_goldens.path(key))
            times, keys = read_signatures(data)
            with self.subTest(key=key):
                self.assertEqual([[t.numerator, t.denominator] for t in times], _goldens.fact(key, "meters"))
                self.assertEqual([t.tick for t in times], _goldens.fact(key, "meter_ticks"))
                self.assertEqual([k.number for k in keys], _goldens.fact(key, "keys"))
                self.assertEqual([k.tick for k in keys], _goldens.fact(key, "key_ticks"))
                if _goldens.fact(key, "key_names"):
                    self.assertEqual([k.name for k in keys], _goldens.fact(key, "key_names"))
                if _goldens.fact(key, "change_bar"):
                    self.assertEqual(meter(data).bar(times[1].tick), float(_goldens.fact(key, "change_bar")))


if __name__ == "__main__":
    unittest.main()
