"""Audio files and the regions that play them, read from Logic's imports of two WAVs onto a
blank-born project (2026-09-13, the public `audio-*` goldens).

An import adds an `lFuA` file record and a `gRuA` region record before the first `lytS`, and an
80-byte entry of type 0x24 in the song container (`regions.py`) whose `+44` word is four times
a counter; the counters of every audio entry in every sequence (take folders included), in
ascending order, are the region records in file order (the counter keeps counting past deleted
regions, so neither the counter nor its distance from the smallest is an index). The file record: `+8` the name's length in UTF-16 units and the name
(UTF-16, big-endian), then `LFUA`; from that magic, `+139` the Media folder's path in a NUL-padded buffer,
`+407` u32 file size, `+457` the format as a reversed four-CC (`EVAW`), `+465` u32 data offset,
`+469` u32 frames, `+477` u32 sample rate, `+481` u16 channels, `+483` u16 bits — the file as
Logic stored it, converted to the project's rate. The region record: `+22` u32 length in frames,
`+74` the name (u16 length, then the text), `+6` u32 the region's first frame within the file
(52920 on a take recorded with a one-bar count-in); its file is the record made with it, in order.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .events import BAR_ONE, PPQ
from .insert import HEADER, project_records
from .midi import ENTRY_TICK_AT, REGION_BAR_ONE
from .regions import ENTRY, TAIL, TRACK_OBJECT_AT, TRACK_ROW_AT, entry_offsets, song_container
from .sequence import sequences
from .stacks import read_tracks
from .tracklist import arrange_run

FILE_TAG, REGION_TAG = b"lFuA", b"gRuA"
AUDIO_ENTRY = 0x24
ENTRY_ORDINAL_AT = 44
NAME_LEN_AT = 8
PATH_AT, SIZE_AT, FORMAT_AT, OFFSET_AT, FRAMES_AT, RATE_AT, CHANNELS_AT, BITS_AT = 139, 407, 457, 465, 469, 477, 481, 483
REGION_OFFSET_AT, REGION_FRAMES_AT, REGION_NAME_AT = 6, 22, 74


@dataclass(frozen=True)
class AudioFile:
    name: str
    folder: str
    size: int
    format: str
    data_offset: int
    frames: int
    rate: int
    channels: int
    bits: int


@dataclass(frozen=True)
class AudioRegion:
    track: str
    row: int
    name: str
    start: int                 # absolute tick, bar 1 at 38400
    frames: int
    file: AudioFile | None
    offset: int = 0            # the region's first frame within its file
    object_id: int = 0         # the track object the entry names

    @property
    def start_bar(self) -> float:
        return (self.start - BAR_ONE) / (PPQ * 4) + 1


def _file(payload: bytes) -> AudioFile:
    n = payload[NAME_LEN_AT]
    name = payload[NAME_LEN_AT + 1:NAME_LEN_AT + 1 + 2 * n].decode("utf-16-be")
    m = NAME_LEN_AT + 1 + 2 * n
    folder = payload[m + PATH_AT:m + FORMAT_AT].split(b"\0", 1)[0].decode("utf-8", "replace")
    u32 = lambda at: struct.unpack_from("<I", payload, m + at)[0]  # noqa: E731
    u16 = lambda at: struct.unpack_from("<H", payload, m + at)[0]  # noqa: E731
    return AudioFile(name, folder, u32(SIZE_AT), payload[m + FORMAT_AT:m + FORMAT_AT + 4][::-1].decode("latin-1"),
                     u32(OFFSET_AT), u32(FRAMES_AT), u32(RATE_AT), u16(CHANNELS_AT), u16(BITS_AT))


def read_audio_files(data: bytes) -> list[AudioFile]:
    return [_file(r.raw[HEADER:]) for r in project_records(data) if r.tag == FILE_TAG]


def _region_name(payload: bytes) -> str:
    n = struct.unpack_from("<H", payload, REGION_NAME_AT)[0]
    return payload[REGION_NAME_AT + 2:REGION_NAME_AT + 2 + n].decode("latin-1")


def audio_entry_words(records) -> list[int]:
    """The `+44` word of every audio entry in every sequence (take folders included)."""
    words = []
    for t in sequences(records):
        events = records[t.end].raw[HEADER:]
        if len(events) < ENTRY + TAIL:
            continue
        for off in entry_offsets(events):
            if struct.unpack_from("<H", events, off)[0] == AUDIO_ENTRY:
                words.append(struct.unpack_from("<I", events, off + ENTRY_ORDINAL_AT)[0])
    return words


def region_ranks(records) -> dict[int, int]:
    """Entry counter -> index of its region record: the counters of every audio entry in every
    sequence (take folders included), in ascending order, are the records in file order."""
    return {c: k for k, c in enumerate(sorted({w // 4 for w in audio_entry_words(records)}))}


def read_audio_regions(data: bytes, track_count: int | None = None) -> list[AudioRegion]:
    """Every audio region in the song container's order, with the file its record was made with."""
    records = project_records(data)
    run = arrange_run(records, track_count)
    song = song_container(records, run)
    if song is None:
        return []
    names = {r["object_id"]: r["name"] for r in read_tracks(data, track_count)}
    files = read_audio_files(data)
    region_records = [r.raw[HEADER:] for r in records if r.tag == REGION_TAG]
    payload = records[song.end].raw[HEADER:]
    entries = [payload[off:off + ENTRY] for off in entry_offsets(payload)]
    entries = [e for e in entries if struct.unpack_from("<H", e, 0)[0] == AUDIO_ENTRY]
    rank = region_ranks(records)
    out = []
    for e in entries:
        k = rank.get(struct.unpack_from("<I", e, ENTRY_ORDINAL_AT)[0] // 4)
        if k is None or k >= len(region_records):
            continue
        rec = region_records[k]
        oid = struct.unpack_from("<H", e, TRACK_OBJECT_AT)[0]
        out.append(AudioRegion(names.get(oid, f"object {oid}"), struct.unpack_from("<H", e, TRACK_ROW_AT)[0], _region_name(rec),
                               struct.unpack_from("<I", e, ENTRY_TICK_AT)[0] - REGION_BAR_ONE + BAR_ONE,
                               struct.unpack_from("<I", rec, REGION_FRAMES_AT)[0], files[k] if k < len(files) else None,
                               struct.unpack_from("<I", rec, REGION_OFFSET_AT)[0], oid))
    return out
