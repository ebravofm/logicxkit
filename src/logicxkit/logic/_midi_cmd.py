"""`logic midi` — the MIDI regions of a song, their export as a Standard MIDI File, and on a
copy a new empty region or a note."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ._edit import CommandError, edit_copy, first_project_data
from .services.midi import MidiRegion, read_midi
from .services.midi_write import add_note, add_region
from .services.signature import meter
from .services.smf import meter_map, tempo_map, write_smf
from .services.retrack import find_project


def _describe(e) -> str:
    if e.kind == "note":
        return f"note {e.pitch:3d} vel {e.velocity:3d} len {e.length:5d}"
    if e.kind == "controller":
        return f"cc {e.number:3d} = {e.value}"
    if e.kind == "program":
        return f"program {e.program}"
    if e.kind == "bend":
        return f"bend {e.value}"
    return e.kind


def _print(regions: list[MidiRegion]) -> None:
    for r in regions:
        loop = "  (loop)" if r.loop else ""
        print(f"  {r.track:16s} {r.name!r:20s} bar {r.start_bar:6.2f}  {len(r.events)} event(s){loop}")
        for e in r.events:
            print(f"      bar {e.bar:7.3f}  ch {e.channel:2d}  {_describe(e)}")


def _number(text: str, what: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise CommandError(f"bad {what} {text!r}: a bar number, fractions allowed") from None


def _write(args, project: Path) -> int:
    def step(data, count, data_file):
        m = meter(data)
        for spec in args.region or []:
            parts = spec.split(":")
            if len(parts) not in (3, 4):
                raise CommandError(f"bad --region {spec!r}: TRACK:BAR:BARS[:NAME]")
            start = m.tick(_number(parts[1], "region bar"))
            data, r = add_region(data, track=parts[0], start=start, length=m.ticks(_number(parts[2], "region length"), start),
                                 name=parts[3] if len(parts) == 4 else None, track_count=count)
            print(f"  {r['track']:16s} region {r['name']!r} at bar {parts[1]} for {parts[2]} bar(s), slot {r['slot']}")
        for spec in args.note or []:
            parts = spec.split(":")
            if len(parts) not in (5, 6):
                raise CommandError(f"bad --note {spec!r}: TRACK:BAR:PITCH:VELOCITY:TICKS[:CHANNEL]")
            try:
                data = add_note(data, track=parts[0], tick=m.tick(_number(parts[1], "note bar")), pitch=int(parts[2]),
                                velocity=int(parts[3]), length=int(parts[4]), channel=int(parts[5]) if len(parts) == 6 else 1,
                                track_count=count)
            except ValueError as e:
                raise CommandError(str(e)) from None
            print(f"  {parts[0]:16s} note {parts[2]} at bar {parts[1]}")
        return data
    try:
        edit_copy(project, Path(args.out), step)
    except (ValueError, CommandError) as e:
        print(f"  {e}")
        return 1
    return 0


def cmd_midi(args) -> int:
    project = find_project(Path(args.project))
    if args.region or args.note:
        if not args.out:
            print("  --out is needed to write")
            return 2
        return _write(args, project)
    data = first_project_data(project)
    regions = read_midi(data)
    if args.track:
        regions = [r for r in regions if r.track == args.track]
    note = sys.stderr if args.json else sys.stdout
    if args.export:
        tempos, meters = tempo_map(data), meter_map(data)
        try:
            smf = write_smf(regions, tempos=tempos, meters=meters)
        except ValueError as e:
            print(f"  {e}", file=note)
            return 1
    if args.json:
        print(json.dumps([{"track": r.track, "row": r.row, "name": r.name, "start": r.start, "loop": r.loop,
                           "events": [vars(e) for e in r.events]} for r in regions], indent=1))
    else:
        print(f"{project.name}: {len(regions)} MIDI region(s)")
        _print(regions)
    if args.export:
        out = Path(args.export)
        out.write_bytes(smf)
        print(f"\nout : {out}  ({len(regions)} track(s), {len(tempos)} tempo event(s) from {tempos[0][1]:g} bpm, "
              f"{len(meters)} time signature(s))", file=note)
    return 0


def register(sub) -> None:
    ap = sub.add_parser("midi", help="read a song's MIDI regions, or export them as a .mid file")
    ap.add_argument("project")
    ap.add_argument("--track", metavar="NAME", help="only this track's regions")
    ap.add_argument("--export", metavar="FILE.mid", help="write a format-1 Standard MIDI File with the song's tempo map and time signatures")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="output directory (needed to write)")
    ap.add_argument("--region", action="append", metavar="TRACK:BAR:BARS[:NAME]", help="a new empty MIDI region")
    ap.add_argument("--note", action="append", metavar="TRACK:BAR:PITCH:VELOCITY:TICKS[:CHANNEL]", help="a note in the track's region that holds BAR")
    ap.set_defaults(func=cmd_midi)
