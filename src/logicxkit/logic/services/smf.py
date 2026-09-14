"""A Standard MIDI File (format 1, the project's PPQ) from the regions `midi.read_midi` reads:
track 0 carries the song's tempo events and time signatures, then one track per region named
after its track and region. Bar 1 is the file's tick 0; times are region start plus each
event's offset; a note-off carries velocity 64. The file has no time before bar 1, so an event
there is refused; the meter in force at bar 1 (Logic files it on a bar line before) goes at 0."""

from __future__ import annotations

import struct

from .events import BAR_ONE, PPQ
from .midi import MidiRegion
from .signature import read_signatures
from .tempo import project_tempo, read_tempo_events

NOTE_OFF_VELOCITY = 64
END_OF_TRACK = b"\xff\x2f\x00"


def vlq(n: int) -> bytes:
    """A variable-length quantity, 7 bits per byte, high bit set on all but the last."""
    if n < 0:
        raise ValueError("a delta time is never negative")
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def _chunk(tag: bytes, body: bytes) -> bytes:
    return tag + struct.pack(">I", len(body)) + body


def _track(messages: list[tuple[int, bytes]]) -> bytes:
    """``(absolute tick, message)`` pairs, sorted stably, as an MTrk chunk."""
    body, at = bytearray(), 0
    for tick, msg in sorted(messages, key=lambda m: m[0]):
        body += vlq(tick - at) + msg
        at = tick
    return _chunk(b"MTrk", bytes(body) + b"\x00" + END_OF_TRACK)


def _messages(region: MidiRegion) -> list[tuple[int, bytes]]:
    out: list[tuple[int, bytes]] = []
    for e in region.events:
        tick, ch = e.tick - BAR_ONE, e.channel - 1
        if e.kind == "note":
            out.append((tick, bytes([0x90 | ch, e.pitch, e.velocity])))
            out.append((tick + e.length, bytes([0x80 | ch, e.pitch, NOTE_OFF_VELOCITY])))
        elif e.kind == "controller":
            out.append((tick, bytes([0xB0 | ch, e.number, e.value])))
        elif e.kind == "program":
            out.append((tick, bytes([0xC0 | ch, e.program])))
        elif e.kind == "bend":
            out.append((tick, bytes([0xE0 | ch, e.data1, e.data2])))
    return out


def tempo_map(data: bytes) -> list[tuple[int, float]]:
    """``(absolute tick, bpm)`` for every tempo event, ramp points included; the bar-1 tempo
    alone when the song has no tempo track."""
    return [(e.position, e.bpm) for e in read_tempo_events(data)] or [(BAR_ONE, project_tempo(data)[1])]


def meter_map(data: bytes) -> list[tuple[int, int, int]]:
    """``(absolute tick, numerator, denominator)`` for every time signature."""
    return [(s.tick, s.numerator, s.denominator) for s in read_signatures(data)[0]]


def _conductor(tempos: list[tuple[int, float]], meters: list[tuple[int, int, int]]) -> list[tuple[int, bytes]]:
    early = [t for t, _bpm in tempos if t < BAR_ONE]
    if early:
        raise ValueError(f"a tempo event at tick {early[0]} is before bar 1, which a Standard MIDI File cannot hold")
    out = [(t - BAR_ONE, b"\xff\x51\x03" + round(60_000_000 / bpm).to_bytes(3, "big")) for t, bpm in tempos]
    ordered = sorted(meters)
    placed = [m for m in ordered if m[0] <= BAR_ONE][-1:] + [m for m in ordered if m[0] > BAR_ONE]
    out += [(max(t - BAR_ONE, 0), b"\xff\x58\x04" + bytes([n, d.bit_length() - 1, 24, 8])) for t, n, d in placed]
    return out


def write_smf(regions: list[MidiRegion], *, tempos: list[tuple[int, float]], meters: list[tuple[int, int, int]]) -> bytes:
    """``tempos`` and ``meters`` as `tempo_map` and `meter_map` give them."""
    tracks = [_track(_conductor(tempos, meters))]
    for r in regions:
        if any(e.tick < BAR_ONE for e in r.events):
            raise ValueError(f"region {r.name!r} on {r.track!r} has events before bar 1, which a Standard MIDI File cannot hold")
        name = f"{r.track}: {r.name}".encode("latin-1", "replace")
        tracks.append(_track([(0, b"\xff\x03" + vlq(len(name)) + name)] + _messages(r)))
    return _chunk(b"MThd", struct.pack(">HHH", 1, len(tracks), PPQ)) + b"".join(tracks)
