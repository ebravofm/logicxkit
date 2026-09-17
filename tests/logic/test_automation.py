"""The automation event reader and writer on hand-built lines: the fader event the writer emits
reads back as its lane with its sub-tick fraction, a parameter point keeps its undecoded flag
bit, and the writer's bounds and order are Logic's."""

import struct
import unittest

from logicxkit.logic.services.automation import PARAM_FLAG, PARAM_POINT, Point, _lanes
from logicxkit.logic.services.automation_write import MAX_TICK, _order, fader_event
from logicxkit.logic.services.events import END_TYPE, LINE
from logicxkit.logic.services.groups import FADER_IDS

VOLUME, PAN = FADER_IDS["Volume"], FADER_IDS["Pan"]
END = struct.pack("<HHI", END_TYPE, 0, 0x3FFFFFFF).ljust(LINE, b"\0")


def param_point(tick: int, value: float, index: int, flag: int = 0, fraction: int = 0) -> bytes:
    head = bytearray(LINE)
    struct.pack_into("<HHI", head, 0, PARAM_POINT | flag, fraction, tick)
    struct.pack_into("<f", head, 8, value)
    head[12] = index
    return bytes(head)


def lanes(payload: bytes) -> dict:
    out: dict = {}
    _lanes(payload, out)
    return out


class ReaderTest(unittest.TestCase):
    def test_a_written_fader_event_reads_as_its_lane_with_its_fraction(self):
        got = lanes(fader_event(38399, 90, VOLUME, fraction=0x8000) + fader_event(42240, 64, VOLUME, relative=True) + END)
        self.assertEqual(sorted(got), [("fader", VOLUME, False), ("fader", VOLUME, True)])
        self.assertEqual([(p.tick, p.fraction, p.position, p.value) for p in got[("fader", VOLUME, False)]],
                         [(38399, 0x8000, 38399.5, 90.0)])
        self.assertEqual([(p.tick, p.value) for p in got[("fader", VOLUME, True)]], [(42240, 64.0)])

    def test_a_flagged_parameter_point_is_read_not_dropped(self):
        got = lanes(param_point(38400, 0.5, 3) + param_point(40000, 0.0, 3, PARAM_FLAG) + END)
        (points,) = got.values()
        self.assertEqual([(p.tick, p.flagged) for p in points], [(38400, False), (40000, True)])
        self.assertEqual(list(got), [("param", 3, False)])

    def test_nothing_after_the_end_marker_is_read(self):
        self.assertEqual(lanes(END + param_point(38400, 0.5, 3)), {})

    def test_a_point_carries_its_position(self):
        self.assertEqual(Point(38400, 90.0, 0x4000).position, 38400.25)


class WriterTest(unittest.TestCase):
    def test_the_event_shape(self):
        e = fader_event(38400, 40, PAN)
        self.assertEqual(e.hex(), "50000000009600000000002" + "80a000000")
        self.assertEqual(fader_event(38400, 64, VOLUME, relative=True)[:2].hex(), "5080")
        self.assertEqual(fader_event(38399, 90, VOLUME, fraction=0x8000)[2:4].hex(), "0080")

    def test_the_bounds(self):
        self.assertEqual(MAX_TICK, 0x7FFFFFFF)     # byte 7's top bit is the continuation flag
        for kwargs in ({"value": 128}, {"tick": MAX_TICK + 1}, {"tick": -1}, {"fraction": 0x10000}, {"fader": 999}):
            with self.subTest(kwargs), self.assertRaises(ValueError):
                fader_event(**{"tick": 0, "value": 90, "fader": VOLUME, **kwargs})
        self.assertEqual(len(fader_event(MAX_TICK, 0, VOLUME, fraction=0xFFFF)), LINE)

    def test_logics_order_is_position_then_type_then_fader_then_relative(self):
        """A parameter point with an index below every fader id still sorts after the fader points
        at its position, and a half-tick splits two points at one tick: each key term is needed."""
        param = param_point(38400, 0.5, 3)                       # 3 is also Solo's fader id
        raws = [fader_event(38400, 90, PAN), param, fader_event(38400, 64, VOLUME, relative=True),
                fader_event(38399, 90, VOLUME, fraction=0x8000), fader_event(38400, 90, VOLUME),
                fader_event(38400, 90, VOLUME, fraction=0x8000), fader_event(38400, 64, PAN, fraction=0x4000)]
        got = sorted(raws, key=_order)
        self.assertEqual(got, [raws[3], raws[4], raws[2], raws[0], param, raws[6], raws[5]])


if __name__ == "__main__":
    unittest.main()
