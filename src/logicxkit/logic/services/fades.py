"""An audio region's fades, in the last sixteen bytes of its song-container entry (`regions.py`),
measured on Logic's Region inspector edits of one region (2026-09-15, the `regions-a15-…` goldens):

    +65   u8    Fade-In type: 0 In, 1 Speed Up        +75   u8    Fade-Out curve, -99..99
    +72   u16   Fade-Out, ms                          +76   u16   Fade-In, ms
                                                      +79   u8    Fade-In curve

+66..+68 changed once, when a drag in X-Fade mode overlapped two regions (`20 05 f9` on the
region underneath, 0x80 at +66 on the one dragged over it); they are read as raw bytes and
never written. The Fade-Out type popup (Out, X, EqP, X S) is unmeasured.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

IN_TYPE_AT, OUT_MS_AT, OUT_CURVE_AT, IN_MS_AT, IN_CURVE_AT = 65, 72, 75, 76, 79
CROSSFADE_AT = slice(66, 69)
IN_TYPES = {0: "in", 1: "speed-up"}
MAX_MS, MAX_CURVE = 0xFFFF, 99


@dataclass(frozen=True)
class Fade:
    in_ms: int = 0
    in_curve: int = 0
    in_type: int = 0
    out_ms: int = 0
    out_curve: int = 0

    def __str__(self) -> str:
        parts = []
        if self.in_ms:
            parts.append(f"in {self.in_ms} ms" + (f" curve {self.in_curve}" if self.in_curve else "")
                         + (f" {IN_TYPES.get(self.in_type, self.in_type)}" if self.in_type else ""))
        if self.out_ms:
            parts.append(f"out {self.out_ms} ms" + (f" curve {self.out_curve}" if self.out_curve else ""))
        return ", ".join(parts)


def _curve(b: int) -> int:
    return b - 256 if b > 127 else b


def read_fade(entry: bytes) -> Fade:
    return Fade(struct.unpack_from("<H", entry, IN_MS_AT)[0], _curve(entry[IN_CURVE_AT]), entry[IN_TYPE_AT],
                struct.unpack_from("<H", entry, OUT_MS_AT)[0], _curve(entry[OUT_CURVE_AT]))


def crossfade_bytes(entry: bytes) -> bytes:
    return entry[CROSSFADE_AT]


def check_fade(fade: Fade) -> None:
    for ms in (fade.in_ms, fade.out_ms):
        if not 0 <= ms <= MAX_MS:
            raise ValueError(f"a fade of {ms} ms: 0 to {MAX_MS}")
    for curve in (fade.in_curve, fade.out_curve):
        if not -MAX_CURVE <= curve <= MAX_CURVE:
            raise ValueError(f"a fade curve of {curve}: -{MAX_CURVE} to {MAX_CURVE}")
    if fade.in_type not in IN_TYPES:
        raise ValueError(f"fade-in type {fade.in_type}: " + ", ".join(f"{k} {v}" for k, v in IN_TYPES.items()))


def with_fade(entry: bytes, fade: Fade) -> bytes:
    """``entry`` carrying ``fade``; the crossfade bytes are kept."""
    check_fade(fade)
    e = bytearray(entry)
    struct.pack_into("<H", e, IN_MS_AT, fade.in_ms)
    struct.pack_into("<H", e, OUT_MS_AT, fade.out_ms)
    e[IN_CURVE_AT], e[OUT_CURVE_AT], e[IN_TYPE_AT] = fade.in_curve & 0xFF, fade.out_curve & 0xFF, fade.in_type
    return bytes(e)
