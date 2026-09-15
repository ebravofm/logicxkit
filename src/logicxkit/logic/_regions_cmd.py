"""`logic regions` — every region on every track, numbered: MIDI ones with their events, audio
ones with their files, mutes, loops and fades; on a copy, `--audio` imports a WAV as a new
region and the edits take a listing number (`region_edit.py`)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ._edit import CommandError, edit_copy, first_project_data
from .services.audio_regions import read_audio_files
from .services.audio_write import add_audio_region
from .services.project import first_alternative, project_metadata
from .services.region_edit import (
    listed, located, move_region, rename_region, renumbered, samples_per_tick_of, set_fade, set_loop, set_mute, split_region,
    trim_region,
)
from .services.retrack import find_project
from .services.signature import meter


def _number(text: str, what: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise CommandError(f"bad {what} {text!r}: a bar number, fractions allowed") from None


def _index(text: str, flag: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise CommandError(f"bad --{flag} {text!r}: N is a region's number in the listing")
    return int(text)


def _split(spec: str, flag: str, shape: str) -> tuple[int, str]:
    n, sep, rest = spec.partition("=")
    if not sep:
        raise CommandError(f"bad --{flag} {spec!r}: {shape}")
    return _index(n, flag), rest


def _switch(spec: str, flag: str) -> tuple[int, bool]:
    n, _sep, rest = spec.partition("=")
    if rest not in ("", "on", "off"):
        raise CommandError(f"bad --{flag} {spec!r}: N, N=on or N=off")
    return _index(n, flag), rest != "off"


def _fade(spec: str, flag: str) -> tuple[int, int, int, int]:
    n, rest = _split(spec, flag, "N=MS[:CURVE[:speed-up]]")
    parts = rest.split(":")
    try:
        ms, curve = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        raise CommandError(f"bad --{flag} {spec!r}: N=MS[:CURVE[:speed-up]]") from None
    kind = parts[2] if len(parts) > 2 else ""
    if kind not in ("", "in", "speed-up") or (flag == "fade-out" and kind):
        raise CommandError(f"bad --{flag} {spec!r}: the type is `speed-up` on a fade-in only")
    return n, ms, curve, int(kind == "speed-up")


class _Tempo:
    """Samples per tick, read only when an edit converts frames — a song whose tempo changes can
    still be muted, renamed or imported into."""

    def __init__(self, data: bytes, rate: int | None):
        self.data, self.rate, self.spt = data, rate, None

    def __call__(self) -> float | None:
        if self.spt is None and self.rate:
            self.spt = samples_per_tick_of(self.data, self.rate)
        return self.spt


def _targets(args, data, count) -> dict:
    """Each edit's region as the listed alternative numbers it: (kind, track, name, start), the
    same region in every alternative."""
    out = {}
    for flag, spec in args.edits:
        loc = located(data, _index(spec.partition("=")[0], flag), count)
        out[(flag, spec)] = (loc.kind, loc.region.track, loc.region.name, loc.region.start)
    return out


def _matched(targets: dict, data, count, alternative: str, listed_alternative: str) -> dict:
    """Each target found in ``data`` (one alternative) -> its `Located`: by number in the listed
    alternative, by track, name and start in the others, where exactly one must match."""
    regions = listed(data, count)
    out = {}
    for (flag, spec), (kind, track, name, start) in targets.items():
        if alternative == listed_alternative:
            out[(flag, spec)] = regions[_index(spec.partition("=")[0], flag) - 1]
            continue
        hits = [loc for loc in regions if (loc.kind, loc.region.track, loc.region.name, loc.region.start) == (kind, track, name, start)]
        if len(hits) != 1:
            has = f"{len(hits)} regions" if hits else "no region"
            raise CommandError(f"--{flag} {spec}: alternative {alternative} has {has} {name!r} on {track!r} "
                               f"at bar {meter(data).bar(start):g}")
        out[(flag, spec)] = hits[0]
    return out


def _edits(args, data, count, tempo: _Tempo, idents: dict) -> bytes:
    """The edits in command-line order, each on the region its number named in the input."""
    m = meter(data)
    for flag, spec in args.edits:
        n = renumbered(data, idents[(flag, spec)], count)
        if flag == "move":
            _n, bar = _split(spec, flag, "N=BAR")
            data = move_region(data, n, m.tick(_number(bar, "bar")), count)
        elif flag == "trim":
            _n, rest = _split(spec, flag, "N=BAR:BARS (either may be empty)")
            start, _sep, bars = rest.partition(":")
            tick = m.tick(_number(start, "bar")) if start else None
            length = None
            if bars:
                first = _number(start, "bar") if start else m.bar(located(data, n, count).region.start)
                length = m.tick(first + _number(bars, "length")) - m.tick(first)
            data = trim_region(data, n, start=tick, length=length, spt=tempo(), track_count=count)
        elif flag == "split":
            _n, bar = _split(spec, flag, "N=BAR")
            data = split_region(data, n, m.tick(_number(bar, "bar")), spt=tempo(), track_count=count)
        elif flag == "loop":
            _n, on = _switch(spec, flag)
            data = set_loop(data, n, on, spt=tempo() if located(data, n, count).audio else None, track_count=count)
        elif flag == "mute":
            _n, on = _switch(spec, flag)
            data = set_mute(data, n, on, count)
        elif flag == "rename":
            _n, name = _split(spec, flag, "N=NAME")
            data = rename_region(data, n, name, count)
        else:
            _n, ms, curve, kind = _fade(spec, flag)
            have = located(data, n, count)
            if have.audio is None:
                raise CommandError(f"region {n} is a MIDI region; fades are an audio region's")
            fade = have.audio.fade
            fade = replace(fade, in_ms=ms, in_curve=curve, in_type=kind) if flag == "fade-in" else replace(fade, out_ms=ms, out_curve=curve)
            data = set_fade(data, n, fade, count)
    return data


def _moved(targets: dict, data, count, data_file: Path, listed_alternative: str) -> list:
    """The keys of the regions an edit moves or cuts in this alternative, for the gate."""
    found = _matched(targets, data, count, data_file.parent.name, listed_alternative)
    return [loc.key for (flag, _spec), loc in found.items() if flag in ("move", "trim", "split")]


def _write(args, project: Path) -> int:
    listed_alternative = first_alternative(project)
    targets = _targets(args, first_project_data(project), project_metadata(project).get("tracks"))

    def step(data, count, data_file):
        bundle = data_file.parents[2]
        rate = project_metadata(bundle, data_file.parent.name).get("sample_rate")
        idents = {edit: loc.ident for edit, loc in _matched(targets, data, count, data_file.parent.name, listed_alternative).items()}
        for spec in args.audio or ():
            parts = spec.split(":", 2)
            if len(parts) != 3:
                raise CommandError(f"bad --audio {spec!r}: TRACK:BAR:FILE.wav")
            wav = Path(parts[2]).expanduser()
            if not wav.is_file():
                raise CommandError(f"no such file: {wav}")
            data, r = add_audio_region(data, track=parts[0], start=meter(data).tick(_number(parts[1], "bar")), wav=wav,
                                       media_folder=bundle / "Media" / "Audio Files", rate=rate, track_count=count)
            print(f"  {r['track']:16s} {r['file']} at bar {parts[1]}: {r['frames']} frames as region {r['name']!r}")
        data = _edits(args, data, count, _Tempo(data, rate), idents)
        for flag, spec in args.edits:
            print(f"  --{flag} {spec}")
        return data
    try:
        edit_copy(project, Path(args.out), step,
                  moved=lambda data, count, data_file: _moved(targets, data, count, data_file, listed_alternative))
    except (ValueError, CommandError) as e:
        print(f"  {e}")
        return 1
    return 0


def _listing(project: Path, args) -> int:
    data = first_project_data(project)
    count = project_metadata(project).get("tracks")
    regions = listed(data, count)
    files = read_audio_files(data)
    if args.track:
        regions = [r for r in regions if r.region.track == args.track]
    if args.json:
        midi = [{"number": r.number, "track": r.midi.track, "row": r.midi.row, "name": r.midi.name, "start": r.midi.start,
                 "loop": r.midi.loop, "muted": r.midi.muted, "events": len(r.midi.events)} for r in regions if r.midi]
        audio = [{"number": r.number, "track": r.audio.track, "row": r.audio.row, "name": r.audio.name, "start": r.audio.start,
                  "frames": r.audio.frames, "offset": r.audio.offset, "piece": r.audio.piece, "loop": r.audio.loop,
                  "muted": r.audio.muted, "fade": vars(r.audio.fade), "file": vars(r.audio.file) if r.audio.file else None}
                 for r in regions if r.audio]
        print(json.dumps({"midi": midi, "audio": audio, "files": [vars(f) for f in files]}, indent=1))
        return 0
    n_midi, n_audio = sum(1 for r in regions if r.midi), sum(1 for r in regions if r.audio)
    print(f"{project.name}: {n_midi} MIDI region(s), {n_audio} audio region(s), {len(files)} audio file(s)")
    for loc in regions:
        r = loc.region
        marks = ("  (loop)" if r.loop else "") + ("  (muted)" if r.muted else "")
        if loc.midi:
            print(f"  {loc.number:3d} {r.track or '-':16s} {r.name!r:22s} bar {r.start_bar:6.2f}  MIDI   {len(r.events)} event(s){marks}")
        else:
            f = r.file
            src = f"{f.name} {f.rate} Hz {f.channels} ch {f.bits} bit" if f else "(file record missing)"
            fade = f"  fade {r.fade}" if str(r.fade) else ""
            offset = f" from {r.offset}" if r.offset else ""
            print(f"  {loc.number:3d} {r.track or '-':16s} {r.name!r:22s} bar {r.start_bar:6.2f}  audio  {r.frames} frames{offset}  {src}{marks}{fade}")
    return 0


def cmd_regions(args) -> int:
    project = find_project(Path(args.project))
    args.edits = [(flag, spec) for flag, spec in (args.edits or ())]
    if args.audio or args.edits:
        if not args.out:
            print("  --out is needed to write")
            return 2
        return _write(args, project)
    return _listing(project, args)


def register(sub) -> None:
    ap = sub.add_parser("regions", help="every MIDI and audio region, numbered, with events or files; edits on a copy")
    ap.add_argument("project")
    ap.add_argument("--track", metavar="NAME", help="only this track's regions")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="output directory (needed to write)")
    ap.add_argument("--audio", action="append", metavar="TRACK:BAR:FILE.wav", help="import a PCM WAV at the project's sample rate as a region")
    for flag, shape, text in (("move", "N=BAR", "start region N at BAR"),
                              ("trim", "N=BAR:BARS", "region N from BAR (content kept in place) for BARS; either may be empty"),
                              ("split", "N=BAR", "cut region N at BAR; the rest becomes a new region"),
                              ("loop", "N[=on|off]", "loop region N (on by default)"),
                              ("mute", "N[=on|off]", "mute region N (on by default)"),
                              ("rename", "N=NAME", "rename region N"),
                              ("fade-in", "N=MS[:CURVE[:speed-up]]", "fade in over MS ms, curve -99..99"),
                              ("fade-out", "N=MS[:CURVE]", "fade out over MS ms, curve -99..99")):
        ap.add_argument(f"--{flag}", dest="edits", action="append", type=lambda s, f=flag: (f, s), metavar=shape, help=text)
    ap.set_defaults(func=cmd_regions)
