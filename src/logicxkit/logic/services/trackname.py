"""A track by the name a user types: `Drums`, or `Drums (Sub 1)` where a stack header and a
channel share the name — the mixer label in parentheses picks the row."""

from __future__ import annotations


def rows_named(rows: list[dict], name: str) -> list[dict]:
    """The `read_tracks` rows ``name`` means. A trailing ``(LABEL)`` is a label only when a row
    has that name and label, so a track literally named `Pad (dry)` still matches itself."""
    wanted = name.strip()
    if wanted.endswith(")") and " (" in wanted:
        base, _, label = wanted[:-1].rpartition(" (")
        labelled = [r for r in rows if r["name"] == base and r["label"] == label]
        if labelled:
            return labelled
    return [r for r in rows if r["name"] == wanted]


def one_object(rows: list[dict], name: str) -> int:
    """The one track object ``name`` means, or a ValueError naming the choices."""
    hits = rows_named(rows, name)
    ids = sorted({r["object_id"] for r in hits})
    if len(ids) == 1:
        return ids[0]
    if not ids:
        raise ValueError(f"no track named {name!r}")
    choices = ", ".join(f"{r['name']} ({r['label']})" for r in hits)
    raise ValueError(f"{len(ids)} tracks named {name!r}; say which: {choices}")
