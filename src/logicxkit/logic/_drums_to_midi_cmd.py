"""`drums-to-midi`: drum hits in audio tracks to notes in a MIDI region, on a copy, without Logic."""

from __future__ import annotations

from pathlib import Path

from ._edit import CommandError, edit_copy
from ._quantize_cmd import _wav_finder


def parse_hits(specs: list[str] | None) -> list[tuple[str, str]]:
    """``TRACK=TERM`` specs -> (track, term); a term is lower-cased with its spaces collapsed."""
    out = []
    for spec in specs or []:
        track, sep, term = spec.rpartition("=")
        term = " ".join(term.split()).lower()
        if not sep or not track.strip() or not term:
            raise CommandError(f"bad --hit {spec!r}: TRACK=TERM")
        out.append((track.strip(), term))
    return out


def detector_of(args):
    """The onset detector, its floor under the track's loudest hit moved by ``--threshold``."""
    from .services.onsets import Detector

    if args.threshold is None:
        return Detector()
    if args.threshold > 0:
        raise CommandError(f"--threshold {args.threshold:g}: dB under the track's loudest hit, 0 or below")
    return Detector(floor_db=args.threshold)


def cmd_drums_to_midi(args) -> int:
    from groovebin.transforms import grid_ticks

    from .services.drums_to_midi import drums_to_midi, note_for
    from .services.events import PPQ

    if not args.out:
        print("  --out is needed to write")
        return 2
    try:
        hits = parse_hits(args.hit)
        detector = detector_of(args)
        for _track, term in hits:
            note_for(args.map, term)
        if args.grid is not None:
            grid_ticks(args.grid, PPQ)
    except (CommandError, ValueError) as e:
        print(f"  {e}")
        return 2

    def step(data, count, project_file):
        data, report = drums_to_midi(data, hits=hits, target=args.track, wav_of=_wav_finder(Path(project_file), args.audio),
                                     map_name=args.map, grid=args.grid, detector=detector, track_count=count)
        for line in report.lines():
            print(f"  {line}")
        return data

    try:
        edit_copy(Path(args.project), Path(args.out), step)
    except (CommandError, ValueError) as e:
        print(f"  {e}")
        return 1
    return 0


def register(sub) -> None:
    from groovebin.maps import NAMES

    from .services.onsets import Detector

    dp = sub.add_parser("drums-to-midi", help="drum hits in audio tracks to notes in a new MIDI region on a software "
                        "instrument track, on a copy, without Logic")
    dp.add_argument("project")
    dp.add_argument("--out", help="output directory (needed to write)")
    dp.add_argument("--hit", action="append", required=True, metavar="TRACK=TERM",
                    help="an audio track and the drum map term its hits play: kick, snare, hihat closed ... (repeatable)")
    dp.add_argument("--track", required=True, metavar="TARGET", help="the software instrument track the region goes on")
    dp.add_argument("--map", choices=NAMES, default="addictive-drums-2",
                    help="the drum map the terms resolve in (default addictive-drums-2)")
    dp.add_argument("--grid", type=int, metavar="N", help="quantize the notes to 1/N (1, 2, 4, 8, 16, 32 or 64); else the take's timing is kept")
    dp.add_argument("--threshold", type=float, metavar="DB",
                    help=f"a hit is at most DB under the track's loudest hit (default {Detector.floor_db:g}); "
                    "lower finds quieter hits")
    dp.add_argument("--audio", metavar="DIR", help="a folder holding the regions' audio files, when they are not "
                    "where the project says")
    dp.set_defaults(func=cmd_drums_to_midi)
