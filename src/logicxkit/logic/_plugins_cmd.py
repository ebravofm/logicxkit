"""`logic plugins` — the plug-ins a project (or every project under a folder) references, and
which of them this Mac lacks."""

from __future__ import annotations

import json
from pathlib import Path

from ._edit import first_project_data
from .services.plugins import installed_components, project_plugins, verdict
from .services.retrack import find_project


def _projects(path: Path) -> list[Path]:
    if path.suffix == ".logicx" or (path / "Alternatives").is_dir():
        return [find_project(path)]
    return sorted(p for p in path.rglob("*.logicx") if (p / "Alternatives").is_dir())


def cmd_plugins(args) -> int:
    projects = _projects(Path(args.project))
    installed = installed_components()
    report = []
    for project in projects:
        v = verdict(project_plugins(first_project_data(project)), installed)
        report.append({"project": str(project), "clean": v.clean,
                       "slots": [{"channel": r.channel, "key": r.key, "name": r.name, "native": r.native,
                                  "component": list(r.component) if r.component else None, "status": s}
                                 for r, s in v.slots]})
        if args.json:
            continue
        summary = "clean" if v.clean else f"{len(v.missing)} missing"
        if installed is None:
            summary = "third-party status unknown (no auval on this machine)"
        print(f"{project.name}: {len(v.slots)} plug-in slot(s), {summary}")
        if len(projects) == 1 or not v.clean:
            for r, status in v.slots:
                if len(projects) > 1 and status != "missing":
                    continue
                ident = " ".join(r.component) if r.component else "native"
                print(f"  {r.channel:16s} key {r.key:2d}  {r.name:28s} {ident:16s} {status}")
    if args.json:
        print(json.dumps(report, indent=1))
    elif len(projects) > 1:
        bad = [r for r in report if not r["clean"]]
        print(f"\n{len(projects)} project(s), {len(bad)} with missing plug-ins")
    return 0 if all(r["clean"] for r in report) else 1


def register(sub) -> None:
    ap = sub.add_parser("plugins", help="which plug-ins a project references and which this Mac lacks")
    ap.add_argument("project", help="a .logicx bundle, or a folder to scan")
    ap.add_argument("--json", action="store_true")
    ap.set_defaults(func=cmd_plugins)
