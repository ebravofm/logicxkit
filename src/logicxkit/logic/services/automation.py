"""Track automation, read from the per-channel ``*Automation`` folders under the ``Track
Automation Root Folder``.

A folder's ``qeSM`` carries the name ``*Automation`` at payload +18, its track's object at ``+234``
and its sequence id at ``+8``, the owner of the ``qSvE`` that holds the points as 16-byte events:
the type word at +0, the sub-tick fraction at +2 (u16; 0x8000 is half a tick — Logic's
region-border point sits at 38399 + 0x8000, half a tick before the region), the tick at +4.
Type 0x50 is a fader point: fader id at head +12, value byte at head +11 (unity 90); the
relative lane — Logic's "± Volume" — sets bit 15 of the type word (0x8050), its value 64 at
0 dB. 0x51 is a plug-in parameter point: 0..1 float at head +8, parameter index at head +12;
bit 14 of its type word (0x4051) reads as ``flagged``, meaning unknown. Head +15 is the
selection state of a point the Event List just made (1, 0x81 on the anchor), rewritten on every
save. A folder keeps its points in (tick, fraction, type, fader, relative) order. A region's own automation
(Convert … to Region Automation) is a sequence nothing references, naming its track at ``+234``
and holding the same point types; region note sequences are referenced from their track's
sequence and hold MIDI, so only folders and unreferenced sequences with points are read.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .events import events
from .groups import FADER_IDS
from .insert import HEADER, project_records
from .sequence import QESM_ID_AT, QESM_OBJECT_AT, sequences
from .stacks import read_tracks

NAME_AT = 18
FOLDER_NAME = b"*Automation"
ROOT_NAME = b"Track Automation Root Folder"
FADER_POINT, PARAM_POINT, REFERENCE = 0x50, 0x51, 0x20
RELATIVE = 0x8000                               # the type word's bit 15: a relative lane
PARAM_FLAG = 0x4000                             # bit 14 on a parameter point: undecoded
FRACTION_UNIT = 0x10000                         # head +2 counts sixty-four-thousandths of a tick
FADER_NAMES = {i: n for n, i in FADER_IDS.items()}


@dataclass(frozen=True)
class Point:
    tick: int
    value: float          # the fader byte of a fader lane; the 0..1 float of a parameter lane
    fraction: int = 0     # head +2: 0x8000 is half a tick
    flagged: bool = False # a parameter point whose type word carries bit 14

    @property
    def position(self) -> float:
        return self.tick + self.fraction / FRACTION_UNIT


@dataclass(frozen=True)
class Lane:
    parameter: str
    fader: int | None
    param_index: int | None
    points: tuple[Point, ...]
    region: bool          # the lane is a region's own automation, not the track's
    relative: bool = False


@dataclass(frozen=True)
class Automation:
    sequence: int
    track_object: int     # 0 when the folder names no track
    track: str | None
    lanes: tuple[Lane, ...]


def named(qesm: bytes, name: bytes) -> bool:
    """Whether the sequence's name field is exactly ``name``."""
    return qesm[NAME_AT:NAME_AT + len(name) + 1] == name + b"\0"


def is_fader_point(e) -> bool:
    return e.type & ~RELATIVE == FADER_POINT


def _lanes(payload: bytes, out: dict) -> None:
    """Points by (kind, number, relative) from one payload; other event types are left alone."""
    for e in events(payload):
        if is_fader_point(e):
            key = ("fader", e.head[12], bool(e.type & RELATIVE))
            out.setdefault(key, []).append(Point(e.tick, float(e.head[11]), e.extra))
        elif e.type & ~PARAM_FLAG == PARAM_POINT:
            value = struct.unpack_from("<f", e.head, 8)[0]
            out.setdefault(("param", e.head[12], False), []).append(
                Point(e.tick, value, e.extra, bool(e.type & PARAM_FLAG)))


def read_automation(data: bytes, track_count: int | None = None) -> list[Automation]:
    """Every automation folder with its lanes, in file order; lanes sort their points by position."""
    records = project_records(data)
    names = {r["object_id"]: r["name"] for r in read_tracks(data, track_count)}
    triples = sequences(records)
    referenced = set()
    for t in triples:
        for e in events(records[t.end].raw[HEADER:]):
            if e.type == REFERENCE:
                referenced.add(struct.unpack_from("<I", e.data, 0)[0])
    out = []
    for t in triples:
        qesm = records[t.start].raw[HEADER:]
        folder = named(qesm, FOLDER_NAME)
        if not folder and (t.slot in referenced or named(qesm, ROOT_NAME)):
            continue
        seq_id = struct.unpack_from("<I", qesm, QESM_ID_AT)[0]
        track_object = struct.unpack_from("<I", qesm, QESM_OBJECT_AT)[0]
        found: dict = {}
        _lanes(records[t.end].raw[HEADER:], found)
        if not folder and not found:
            continue
        lanes = []
        region = not folder                          # a sequence the root does not name is a region's
        for (kind, number, relative), points in found.items():
            points = tuple(sorted(points, key=lambda p: (p.tick, p.fraction)))
            if kind == "fader":
                name = FADER_NAMES.get(number, f"fader {number}")
                lanes.append(Lane(f"± {name}" if relative else name, number, None, points, region, relative))
            else:
                lanes.append(Lane(f"plug-in parameter {number}", None, number, points, region))
        out.append(Automation(seq_id, track_object, names.get(track_object), tuple(lanes)))
    return out
