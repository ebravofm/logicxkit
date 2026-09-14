"""MIDI events inside a region's sequence, and the region's place on its track.

Measured 2026-09-13 on Logic 12.3.1's saves of a blank project (the public `midi-*` goldens).
A region is an 80-byte entry in the song container (`regions.py`): `+4` its start tick with
bar 1 at 34560 (the automation root folders sit there; a one-bar region the Event List placed
at 3 1 1 1 reads 42240), `+13` bit 0 its loop flag, `+32` its sequence's slot. The sequence's
`qeSM` carries the region name at `+16` (u16 length, then the text); its `qSvE` holds the
events (`events.py`), each tick region-relative with 38400 at the region's start:

    note            0x9c line: +11 velocity, +12 pitch; a 0x89 line follows, +12 u32 length
    controller      0xBc line: +11 value, +12 number; a 0xBB line follows
    program change  0xCc line: +12 program
    pitch bend      0xEc line: +12 LSB, +11 MSB

``c`` is the channel less one; `+15` bit 7 marks the selected event. Logic files them by
tick, and at one tick program change, controller, notes, then pitch bend.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .events import BAR_ONE, PPQ, Event, events
from .insert import HEADER, project_records
from .regions import ENTRY, placements, song_container
from .sequence import sequences, triple_by_slot
from .stacks import read_tracks
from .tracklist import arrange_run

REGION_BAR_ONE = 34560
ENTRY_TICK_AT, ENTRY_LOOP_AT, ENTRY_SLOT_AT = 4, 13, 32
MIDI_ENTRY = 0x20                   # entry type; 0x24 is an audio region
NAME_AT = 16
DATA1_AT, DATA2_AT = 12, 11
LENGTH_LINE, LENGTH_AT = 0x89, 12
KINDS = {0x90: "note", 0xB0: "controller", 0xC0: "program", 0xE0: "bend"}


@dataclass(frozen=True)
class MidiEvent:
    kind: str                  # note, controller, program, bend
    tick: int                  # absolute, bar 1 at 38400
    channel: int               # 1-16
    data1: int
    data2: int
    length: int = 0            # a note's, in ticks

    @property
    def pitch(self) -> int:
        return self.data1

    @property
    def velocity(self) -> int:
        return self.data2

    @property
    def number(self) -> int:
        return self.data1

    @property
    def program(self) -> int:
        return self.data1

    @property
    def value(self) -> int:
        """A controller's value, or a pitch bend's 14-bit one (8192 at centre)."""
        return (self.data2 << 7 | self.data1) if self.kind == "bend" else self.data2

    @property
    def bar(self) -> float:
        return (self.tick - BAR_ONE) / (PPQ * 4) + 1


@dataclass(frozen=True)
class MidiRegion:
    track: str
    row: int                   # 1-based arrange row
    name: str
    start: int                 # absolute tick, bar 1 at 38400
    loop: bool
    events: list[MidiEvent]

    @property
    def start_bar(self) -> float:
        return (self.start - BAR_ONE) / (PPQ * 4) + 1


def _is_midi(e: Event) -> bool:
    return 0x80 <= (e.type & 0xFF) <= 0xEF


def _event(e: Event, start: int) -> MidiEvent:
    status = e.type & 0xFF
    length = 0
    if status & 0xF0 == 0x90:
        line = e.line(LENGTH_LINE)
        length = struct.unpack_from("<I", line, LENGTH_AT)[0] if line else 0
    return MidiEvent(KINDS.get(status & 0xF0, f"0x{status & 0xF0:02x}"), start + e.tick - BAR_ONE,
                     (status & 0x0F) + 1, e.head[DATA1_AT], e.head[DATA2_AT], length)


def _name(qesm: bytes) -> str:
    n = struct.unpack_from("<H", qesm, HEADER + NAME_AT)[0]
    return qesm[HEADER + NAME_AT + 2:HEADER + NAME_AT + 2 + n].decode("latin-1")


def read_midi(data: bytes, track_count: int | None = None) -> list[MidiRegion]:
    """Every region whose sequence holds only MIDI events (an empty region counts), in the
    song container's order."""
    records = project_records(data)
    run = arrange_run(records, track_count)
    song = song_container(records, run)
    if song is None:
        return []
    names = {r["object_id"]: r["name"] for r in read_tracks(data, track_count)}
    seqs = sequences(records)
    payload = records[song.end].raw[HEADER:]
    out = []
    for off, oid, row in placements(records, track_count):
        entry = payload[off:off + ENTRY]
        if struct.unpack_from("<H", entry, 0)[0] != MIDI_ENTRY:   # a flexed audio entry's +32 names its RBA sequence
            continue
        t = triple_by_slot(seqs, struct.unpack_from("<I", entry, ENTRY_SLOT_AT)[0])
        if t is None:
            continue
        evs = events(records[t.end].raw[HEADER:])
        if not all(_is_midi(e) for e in evs):
            continue
        start = struct.unpack_from("<I", entry, ENTRY_TICK_AT)[0] - REGION_BAR_ONE + BAR_ONE
        out.append(MidiRegion(names.get(oid, f"object {oid}"), row, _name(records[t.start].raw), start,
                              bool(entry[ENTRY_LOOP_AT] & 1), [_event(e, start) for e in evs]))
    return out
