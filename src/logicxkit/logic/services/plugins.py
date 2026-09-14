"""Which plug-ins a project references, and whether this Mac has them.

A native slot carries Logic's `GAMETSPP` block with the plug-in's type id (`_binary.find_blocks`);
a third-party slot embeds an AU preset plist whose `type`, `subtype` and `manufacturer` are the
component identity (`au.services.embed`). The installed set is what `auval -a` lists. Apple's
own components are counted present without asking: Logic ships them.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from ...au.services.aupreset import parse_au_state
from ...au.services.embed import find_au_plists
from .._binary import find_blocks
from .binding import channels
from .chain_report import PLUGIN_NAMES
from .insert import HEADER, project_records
from .project import _plugin_name
from .sends import is_send

APPLE = "appl"
_AUVAL_LINE = re.compile(r"^(.{4}) (.{4}) (.{4})\s+-\s+")


@dataclass(frozen=True)
class PluginRef:
    channel: str
    key: int
    name: str
    native: bool
    component: tuple[str, str, str] | None     # (type, subtype, manufacturer) of a third-party AU


@dataclass(frozen=True)
class Verdict:
    slots: list[tuple[PluginRef, str]]        # status: apple, installed, missing, unknown
    missing: list[PluginRef]

    @property
    def clean(self) -> bool:
        return not self.missing


def _ref(label: str, key: int, payload: bytes) -> PluginRef | None:
    blocks = find_blocks(payload)
    if blocks:
        type_id = blocks[0][1]
        return PluginRef(label, key, _plugin_name(payload) or PLUGIN_NAMES.get(type_id) or f"type {type_id}", True, None)
    for _off, plist in find_au_plists(payload):
        if "manufacturer" not in plist:
            continue
        st = parse_au_state(plist)
        return PluginRef(label, key, f"{st.manufacturer}/{st.subtype}", st.manufacturer == APPLE,
                         (st.type, st.subtype, st.manufacturer))
    return None


def project_plugins(data: bytes) -> list[PluginRef]:
    """Every plug-in slot in record order, with its channel's label."""
    labels = {o: c.label for o, c in channels(data).items()}
    out = []
    for r in project_records(data):
        if r.tag != b"UCuA" or r.owner not in labels or is_send(r):
            continue
        ref = _ref(labels[r.owner], r.key, r.raw[HEADER:])
        if ref is not None:
            out.append(ref)
    return out


def installed_from_auval(text: str) -> set[tuple[str, str, str]]:
    out = set()
    for line in text.splitlines():
        m = _AUVAL_LINE.match(line)
        if m:
            out.add((m.group(1), m.group(2), m.group(3)))
    return out


def installed_components() -> set[tuple[str, str, str]] | None:
    """What `auval -a` lists, or None when the tool is not on this machine."""
    auval = shutil.which("auval")
    if auval is None:
        return None
    run = subprocess.run([auval, "-a"], capture_output=True, text=True, timeout=120)
    return installed_from_auval(run.stdout)


def verdict(refs: list[PluginRef], installed: set[tuple[str, str, str]] | None) -> Verdict:
    slots, missing = [], []
    for ref in refs:
        if ref.native:
            status = "apple"
        elif installed is None:
            status = "unknown"
        elif ref.component in installed:
            status = "installed"
        else:
            status = "missing"
            missing.append(ref)
        slots.append((ref, status))
    return Verdict(slots, missing)
