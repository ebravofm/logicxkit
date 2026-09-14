"""`logic regions` — every region on every track: MIDI ones with their events, audio ones with
their files; on a copy, `--audio` imports a WAV as a new region."""

from __future__ import annotations

import json
from pathlib import Path

from ._edit import CommandError, edit_copy, first_project_data
from .services.audio_regions import read_audio_files, read_audio_regions
from .services.audio_write import add_audio_region
from .services.project import project_metadata
from .services.signature import meter
from .services.midi import read_midi
from .services.retrack import find_project


def _number(text: str, what: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise CommandError(f"bad {what} {text!r}: a bar number, fractions allowed") from None


def _write(args, project: Path) -> int:
    def step(data, count, data_file):
        bundle = data_file.parents[2]
        rate = project_metadata(bundle).get("sample_rate")
        for spec in args.audio:
            parts = spec.split(":", 2)
            if len(parts) != 3:
                raise CommandError(f"bad --audio {spec!r}: TRACK:BAR:FILE.wav")
            wav = Path(parts[2]).expanduser()
            if not wav.is_file():
                raise CommandError(f"no such file: {wav}")
            try:
                data, r = add_audio_region(data, track=parts[0], start=meter(data).tick(_number(parts[1], "bar")), wav=wav,
                                           media_folder=bundle / "Media" / "Audio Files", rate=rate, track_count=count)
            except ValueError as e:
                raise CommandError(str(e)) from None
            print(f"  {r['track']:16s} {r['file']} at bar {parts[1]}: {r['frames']} frames as region {r['name']!r}")
        return data
    try:
        edit_copy(project, Path(args.out), step)
    except (ValueError, CommandError) as e:
        print(f"  {e}")
        return 1
    return 0


def cmd_regions(args) -> int:
    project = find_project(Path(args.project))
    if args.audio:
        if not args.out:
            print("  --out is needed to write")
            return 2
        return _write(args, project)
    data = first_project_data(project)
    midi, audio = read_midi(data), read_audio_regions(data)
    files = read_audio_files(data)
    if args.track:
        midi = [r for r in midi if r.track == args.track]
        audio = [r for r in audio if r.track == args.track]
    if args.json:
        print(json.dumps({"midi": [{"track": r.track, "row": r.row, "name": r.name, "start": r.start, "loop": r.loop, "events": len(r.events)} for r in midi],
                          "audio": [{"track": r.track, "row": r.row, "name": r.name, "start": r.start, "frames": r.frames, "file": vars(r.file) if r.file else None} for r in audio],
                          "files": [vars(f) for f in files]}, indent=1))
        return 0
    print(f"{project.name}: {len(midi)} MIDI region(s), {len(audio)} audio region(s), {len(files)} audio file(s)")
    rows = sorted([(r.row, r.start, k, i, r) for i, r in enumerate(midi) for k in ("midi",)] + [(r.row, r.start, "audio", i, r) for i, r in enumerate(audio)], key=lambda x: x[:4])
    for _row, _start, kind, _i, r in rows:
        if kind == "midi":
            print(f"  {r.track:16s} {r.name!r:22s} bar {r.start_bar:6.2f}  MIDI   {len(r.events)} event(s){'  (loop)' if r.loop else ''}")
        else:
            f = r.file
            src = f"{f.name} {f.rate} Hz {f.channels} ch {f.bits} bit" if f else "(file record missing)"
            print(f"  {r.track:16s} {r.name!r:22s} bar {r.start_bar:6.2f}  audio  {r.frames} frames  {src}")
    return 0


def register(sub) -> None:
    ap = sub.add_parser("regions", help="every MIDI and audio region, with events or files")
    ap.add_argument("project")
    ap.add_argument("--track", metavar="NAME", help="only this track's regions")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="output directory (needed to write)")
    ap.add_argument("--audio", action="append", metavar="TRACK:BAR:FILE.wav", help="import a PCM WAV at the project's sample rate as a region")
    ap.set_defaults(func=cmd_regions)
