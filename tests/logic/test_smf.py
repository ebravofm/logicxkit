"""Standard MIDI File export of the regions `midi.read_midi` returns: format 1, the song's
tempo map and meters on track 0, one track per region."""

import struct
import unittest
from unittest import mock
import _paths  # noqa: F401
from logicxkit.logic.services.events import BAR_ONE, PPQ
from logicxkit.logic.services.midi import MidiEvent, MidiRegion
from logicxkit.logic.services.smf import tempo_map, vlq, write_smf
from logicxkit.logic.services.tempo import TempoEvent

FOUR_FOUR = [(BAR_ONE, 4, 4)]


def region(*events, name="Inst 1", track="Inst 1", start=BAR_ONE + 2 * 4 * PPQ):
    return MidiRegion(track, 2, name, start, False, list(events))


def chunks(smf: bytes) -> list[tuple[bytes, bytes]]:
    out, pos = [], 0
    while pos < len(smf):
        tag, size = smf[pos:pos + 4], struct.unpack_from(">I", smf, pos + 4)[0]
        out.append((tag, smf[pos + 8:pos + 8 + size]))
        pos += 8 + size
    return out


class VlqTest(unittest.TestCase):
    def test_variable_length_quantities(self):
        self.assertEqual([vlq(n) for n in (0, 127, 128, 960, 0x3FFF, 0x4000)],
                         [b"\x00", b"\x7f", b"\x81\x00", b"\x87\x40", b"\xff\x7f", b"\x81\x80\x00"])


class FileTest(unittest.TestCase):
    def test_header_tempo_meter_and_one_track_per_region(self):
        smf = write_smf([region(), region(name="Second")], tempos=[(BAR_ONE, 120.0)], meters=[(960, 3, 4)])
        (head, body), *tracks = chunks(smf)
        self.assertEqual((head, body), (b"MThd", struct.pack(">HHH", 1, 3, PPQ)))
        self.assertEqual([t for t, _ in tracks], [b"MTrk"] * 3)
        tempo_track = tracks[0][1]
        self.assertTrue(tempo_track.startswith(b"\x00\xff\x51\x03" + (60_000_000 // 120).to_bytes(3, "big")))
        self.assertIn(b"\x00\xff\x58\x04\x03\x02\x18\x08", tempo_track)
        self.assertTrue(all(t.endswith(b"\xff\x2f\x00") for _, t in tracks))

    def test_tempo_changes_and_meter_changes_at_their_ticks_from_bar_1(self):
        smf = write_smf([], tempos=[(BAR_ONE, 120.0), (BAR_ONE + 4 * PPQ, 90.0), (BAR_ONE + 4 * PPQ + 1, 140.0)],
                        meters=[(0, 4, 4), (BAR_ONE + 8 * PPQ, 7, 8)])
        track = chunks(smf)[1][1]
        want = (b"\x00\xff\x51\x03" + (500000).to_bytes(3, "big") + b"\x00\xff\x58\x04\x04\x02\x18\x08"
                + vlq(4 * PPQ) + b"\xff\x51\x03" + round(60_000_000 / 90).to_bytes(3, "big")
                + b"\x01\xff\x51\x03" + round(60_000_000 / 140).to_bytes(3, "big")
                + vlq(4 * PPQ - 1) + b"\xff\x58\x04\x07\x03\x18\x08")
        self.assertTrue(track.startswith(want), track.hex())

    def test_a_note_becomes_on_and_off_at_region_relative_times(self):
        start = BAR_ONE + 2 * 4 * PPQ
        note = MidiEvent("note", start + PPQ, 2, 62, 79, length=480)
        smf = write_smf([region(note)], tempos=[(BAR_ONE, 120.0)], meters=FOUR_FOUR)
        track = chunks(smf)[2][1]
        on = vlq(2 * 4 * PPQ + PPQ) + bytes([0x91, 62, 79])
        off = vlq(480) + bytes([0x81, 62, 64])
        self.assertIn(on + off, track)

    def test_controller_program_and_bend(self):
        start = BAR_ONE
        evs = [MidiEvent("program", start, 1, 5, 0), MidiEvent("controller", start, 1, 1, 100),
               MidiEvent("bend", start, 1, 0x00, 0x40)]
        track = chunks(write_smf([region(*evs, start=start)], tempos=[(BAR_ONE, 100.0)], meters=FOUR_FOUR))[2][1]
        self.assertIn(bytes([0x00, 0xC0, 5, 0x00, 0xB0, 1, 100, 0x00, 0xE0, 0x00, 0x40]), track)


class TempoMapTest(unittest.TestCase):
    def test_ramp_points_logic_generated_are_tempo_events_too(self):
        track = [TempoEvent(BAR_ONE, 120.0, False), TempoEvent(BAR_ONE + PPQ, 125.0, True), TempoEvent(BAR_ONE + 2 * PPQ, 130.0, False)]
        with mock.patch("logicxkit.logic.services.smf.read_tempo_events", return_value=track):
            self.assertEqual(tempo_map(b""), [(BAR_ONE, 120.0), (BAR_ONE + PPQ, 125.0), (BAR_ONE + 2 * PPQ, 130.0)])


class BeforeBarOneTest(unittest.TestCase):
    def test_a_region_starting_before_bar_1_with_its_events_after_it_exports(self):
        note = MidiEvent("note", BAR_ONE, 1, 60, 100, length=240)
        smf = write_smf([region(note, start=BAR_ONE - 4 * PPQ)], tempos=[(BAR_ONE, 120.0)], meters=FOUR_FOUR)
        self.assertIn(b"\x00\x90\x3c\x64", chunks(smf)[2][1])

    def test_an_event_before_bar_1_is_refused_naming_its_region(self):
        note = MidiEvent("note", BAR_ONE - PPQ, 1, 60, 100, length=240)
        with self.assertRaisesRegex(ValueError, "'pickup' on 'Inst 1'.*before bar 1"):
            write_smf([region(note, name="pickup", start=BAR_ONE - 4 * PPQ)], tempos=[(BAR_ONE, 120.0)], meters=FOUR_FOUR)

    def test_a_tempo_event_before_bar_1_is_refused(self):
        with self.assertRaisesRegex(ValueError, "tempo event .*before bar 1"):
            write_smf([], tempos=[(BAR_ONE - PPQ, 120.0)], meters=FOUR_FOUR)


if __name__ == "__main__":
    unittest.main()
