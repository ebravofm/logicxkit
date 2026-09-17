"""`logic automation` — each track's automation lanes and points; `--set`, `--copy` and `--clear`
write a lane onto a copy, applied in command-line order."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._edit import CommandError, edit_copy, first_project_data, object_by_name
from .services.automation import FRACTION_UNIT, read_automation
from .services.automation_write import clear_lane, copy_lane, set_lane
from .services.groups import FADER_IDS
from .services.retrack import find_project
from .services.signature import meter


LANES = {**{k.lower(): (v, False) for k, v in FADER_IDS.items()},
         "±volume": (FADER_IDS["Volume"], True), "volume±": (FADER_IDS["Volume"], True),
         "relative volume": (FADER_IDS["Volume"], True), "volume (relative)": (FADER_IDS["Volume"], True)}


class _Edit(argparse.Action):
    """Every write flag lands in one list, in the order typed."""

    def __call__(self, parser, namespace, values, option_string=None):
        edits = getattr(namespace, "edits", None) or []
        edits.append((option_string.lstrip("-"), values))
        namespace.edits = edits


def _lane(text: str) -> tuple[int, bool]:
    lane = LANES.get(text.strip().lower())
    if lane is None:
        raise CommandError(f"no lane {text.strip()!r}; one of Volume, Pan, Mute, Solo or ±Volume")
    return lane


def _points(text: str, bars) -> list[tuple[int, int]]:
    """``90@1,60@5`` -> [(tick, value)] through the song's meter."""
    out = []
    for item in text.split(","):
        value, _, bar = item.strip().partition("@")
        if not bar:
            raise CommandError(f"a point is VALUE@BAR, not {item.strip()!r}")
        try:
            out.append((bars.tick(float(bar)), int(value)))
        except ValueError:
            raise CommandError(f"a point is VALUE@BAR with a whole value and a bar number, not {item.strip()!r}") from None
    return out


def _apply(data: bytes, count, kind: str, spec: str, bars) -> tuple[bytes, str]:
    if kind == "set":
        target, _, points = spec.partition("=")
        track, _, lane = target.partition(":")
        fader, relative = _lane(lane)
        data = set_lane(data, object_by_name(data, track.strip(), count), fader, _points(points, bars), relative=relative)
        return data, f"{track.strip()}: {lane.strip()} = {points.strip()}"
    if kind == "copy":
        src, _, dst = spec.partition("->")
        track, _, lane = src.partition(":")
        fader, relative = _lane(lane)
        data = copy_lane(data, object_by_name(data, track.strip(), count), object_by_name(data, dst.strip(), count), fader, relative=relative)
        return data, f"{track.strip()}: {lane.strip()} -> {dst.strip()}"
    track, _, lane = spec.partition(":")
    fader, relative = _lane(lane)
    data = clear_lane(data, object_by_name(data, track.strip(), count), fader, relative=relative)
    return data, f"{track.strip()}: {lane.strip()} cleared"


def _write(args, project) -> int:
    lines: list[str] = []

    def step(data, count, data_file):
        """Runs once per alternative, so each line says which one it belongs to — otherwise one
        edit reads as several on a project carrying more than one."""
        bars = meter(data)
        for kind, spec in args.edits:
            data, line = _apply(data, count, kind, spec, bars)
            lines.append(f"  {data_file.parent.name}: {line}")
        return data

    print(f"in  : {project}")
    try:
        edit_copy(project, Path(args.out), step)
    except (CommandError, ValueError) as e:
        print(f"  {e}")
        return 1
    print("\n".join(lines))
    print("\nUnverified until opened in Logic.")
    return 0


def cmd_automation(args) -> int:
    project = find_project(Path(args.project))
    if getattr(args, "edits", None):
        if not args.out:
            print("  --out is needed to write")
            return 2
        return _write(args, project)
    data = first_project_data(project)
    folders = [a for a in read_automation(data) if a.lanes or args.all]
    if args.json:
        print(json.dumps([{"sequence": a.sequence, "track": a.track, "track_object": a.track_object,
                           "lanes": [{"parameter": ln.parameter, "fader": ln.fader, "param_index": ln.param_index,
                                      "region": ln.region,
                                      "points": [{"tick": p.tick, "fraction": p.fraction, "value": p.value, "flagged": p.flagged}
                                                 for p in ln.points]}
                                     for ln in a.lanes]} for a in folders], indent=1))
        return 0
    bars = meter(data)
    print(f"{project.name}: {sum(len(a.lanes) for a in folders)} lane(s) on {len(folders)} track(s)")
    for a in folders:
        print(f"  {a.track or f'(no track, sequence {a.sequence})'}")
        for ln in a.lanes:
            where = " (region)" if ln.region else ""
            print(f"    {ln.parameter}{where}: {len(ln.points)} point(s)")
            for p in ln.points:
                value = f"{p.value:.4f}" if ln.param_index is not None else f"{p.value:.0f}"
                print(f"      bar {bars.bar(p.tick + p.fraction / FRACTION_UNIT):9.5f}  {value}{'  ?' if p.flagged else ''}")
    return 0


def register(sub) -> None:
    ap = sub.add_parser("automation", help="track automation lanes and points; --set, --copy and --clear write a copy")
    ap.add_argument("project")
    ap.add_argument("--all", action="store_true", help="list tracks whose folder holds no lane too")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--set", action=_Edit, metavar="TRACK:LANE=V@BAR,...",
                    help="replace a lane's points: values 0-127 (Volume 90 and Pan 64 are unity), bars as the display shows them; lanes Volume, Pan, Mute, Solo, ±Volume")
    ap.add_argument("--copy", action=_Edit, metavar="TRACK:LANE->TRACK", help="the lane onto another track, replacing the target's")
    ap.add_argument("--clear", action=_Edit, metavar="TRACK:LANE", help="remove the lane's points")
    ap.add_argument("--out", help="directory holding the copy to write")
    ap.set_defaults(func=cmd_automation)
