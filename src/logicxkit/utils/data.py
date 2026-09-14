"""Where the data lives: Logic-written record templates, the plugin-slot donor library and the
AU parameter tables. None of it is authored here — Logic and the plugin vendors wrote those
bytes. Two places, the first wins:

    LOGICXKIT_DATA          env override, absolute
    <repo>/resources/data   the default root, gitignored; see resources/data/README.md
    logicxkit/data/         the package's own copy of what Logic wrote on a blank project
                            (`logic/` templates, `donors/` native plug-ins only)

    <root>/donors/*.slot     plugin-slot donors and their manifest (`logic donors` harvests them)
    <root>/logic/*.json      record templates Logic saved (aux, instrument, audio, group, section)
    <root>/au/*.json         AU parameter tables (`au params` regenerates them) — root only
"""

from __future__ import annotations

from pathlib import Path

from .env import env_path

ENV = "LOGICXKIT_DATA"
KINDS = ("donors", "logic", "au")
PACKAGED = Path(__file__).resolve().parents[1] / "data"
PACKAGED_KINDS = ("donors", "logic")


class MissingData(FileNotFoundError):
    """A data file the operation needs is in neither the data root nor the package."""


def data_root() -> Path:
    return env_path(ENV, Path(__file__).resolve().parents[3] / "resources" / "data")


def data_dir(kind: str) -> Path:
    if kind not in KINDS:
        raise ValueError(f"data kind {kind!r} is not one of {KINDS}")
    return data_root() / kind


def data_dirs(kind: str) -> list[Path]:
    """Every directory holding ``kind``, the data root first, the package second."""
    candidates = [data_dir(kind)] + ([PACKAGED / kind] if kind in PACKAGED_KINDS else [])
    return [d for d in candidates if d.is_dir()]


def data_file(kind: str, name: str) -> Path:
    """One data file: the data root's, else the package's, else `MissingData` naming both."""
    for d in data_dirs(kind):
        if (d / name).exists():
            return d / name
    raise MissingData(f"{kind}/{name} is in neither {data_dir(kind)} ({ENV}) nor the package's "
                      "logicxkit/data — Logic- or vendor-written data; resources/data/README.md "
                      "says how each kind is made")


def have_data(kind: str, *names: str) -> bool:
    return any(all((d / n).exists() for n in names) for d in data_dirs(kind))
