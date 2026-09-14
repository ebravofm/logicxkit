"""Create a folder stack from existing arrange rows.

Logic's own Create Track Stack on a blank project is the packaged pattern for a session that has no stack; otherwise this composes the measured pieces — a
track add (`addtrack.py`), a drag into a stack (`stacks.move_to_stack`) and the `Sub` strips
the existing stacks bind to. A folder stack is a kind-0 Environment object bound to a `Sub N`
strip, its arrange row followed by its members' rows with `+14` set. What this writes:

* the object: the highest-numbered stack's, cloned — new id, name, colour, Sub number,
  fresh UUID; the icon stays the pattern's (which icon Logic gives a new stack is unmeasured)
* the strip: `Sub N` cloned as `Sub N+1` right after it, every later channel's owner moved up
  by one (and the objects bound to them re-indexed), the channel count's Master+Sub class
  counted up
* the rows: a header row where the first member sat, expanded and selected; the member rows
  behind it in arrange order with `+14 = 1`, their objects' parent pointer and their
  channels' stack index set as a drag sets them
* the flat mixer-order row after the last Sub's, the sequence triple, the index-table entry
  and the `gnoS` registry entries, as a track add writes them

Members already inside a stack are refused: nesting has not been measured.
`NumberOfTracks` in MetaData.plist is the caller's job.
"""

from __future__ import annotations

import json
import struct

from ...utils.data import data_file
from .binding import bound_channels, channels, set_stack_index
from .channel_alloc import (
    COUNT_CLASS_AT,
    NUMBER_AT,
    bump_channel_count,
    is_channel_count,
    is_channel_record,
    is_mixer_record,
    mixer_record,
    new_sub_channel,
    shifted_channel,
)
from .environment import (
    DEFAULT_COLOUR,
    ENV_TAG,
    STAMP_AT,
    UUID_LEN,
    channel_objects,
    clone_object,
    next_object_id,
    object_id_of,
    object_record,
    object_stamp,
    set_parent,
    shifted_object,
)
from .insert import CHANNEL_BASE_AT, HEADER, project_records, reassemble, slot_index_base
from .keyflags import sync_key_flags
from .recbuild import fresh_uuid, rec
from .registry import GNOS_TAG, register_object
from .regions import sync_region_tracks, sync_row_count
from .selection import select_track
from .sequence import index_table, plan_sequence, table_entries
from .stacks import read_stacks, read_tracks
from .tracklist import (
    arrange_run,
    clone_flat_row,
    flat_run,
    new_row,
    renumbered,
    row_object,
    with_member,
)
from .validate import require_full_walk, require_valid

SUB_NUMBER_AT = NUMBER_AT
_DATA = "stack-folder-12.3.1.json"


def _packaged_pattern() -> dict[str, bytes]:
    """Logic's own first folder stack on a blank project: the `Sub 1` strip, the header object
    and its arrange row (`stack-folder-12.3.1.json`, roles `strip`, `object`, `row`)."""
    t = json.loads(data_file("logic", _DATA).read_text())
    return {role: bytes.fromhex(r["header"]) + bytes.fromhex(r["payload"]) for role, r in t["records"].items()}


def _first_stack(data: bytes, records, chans) -> tuple[int, int, int, bytes, bytes, bytes]:
    """What a stack-less session's first stack patterns on -> ``(number, like, like_owner,
    object, strip, row)``: Logic's own packaged pieces, the strip numbered and placed after the
    last `Sub` strip (else after the Master strip) with the session's slot base, the object
    stamped past every existing one, the sequence shaped like the highest-indexed object's."""
    packaged = _packaged_pattern()
    subs = {int(c.label[4:]): o for o, c in chans.items() if c.label.startswith("Sub ") and c.label[4:].isdigit()}
    if subs:                                          # a flattened stack leaves its strip behind
        number = max(subs) + 1
        after = subs[max(subs)]
    else:
        number = 1
        after = next((o for o, c in chans.items() if c.label == "Master"), None)
        if after is None:
            raise ValueError("no Master strip to place Sub 1 after")
    strip = bytearray(packaged["strip"])
    strip[HEADER + CHANNEL_BASE_AT] = slot_index_base(data)
    top_stamp = max(object_stamp(r.raw) for r in records if r.tag == ENV_TAG and object_id_of(r) is not None)
    obj = bytearray(packaged["object"])
    struct.pack_into("<I", obj, HEADER + STAMP_AT, top_stamp)
    table = records[index_table(records)].raw[HEADER:]
    like = max(table_entries(table), key=lambda e: e[2])[1]
    return number, like, after, bytes(obj), bytes(strip), packaged["row"]


def _members_in_order(rows: list[dict], members: list[int], headers: set[int]) -> list[int]:
    by_object = {r["object_id"]: r for r in rows}
    for m in members:
        row = by_object.get(m)
        if row is None:
            raise ValueError(f"object {m} is not in the arrange list")
        if m in headers:
            raise ValueError(f"object {m} is a stack header; nesting is not modelled")
        if row["member"]:
            raise ValueError(f"{row['name']!r} is already inside a stack; nesting is not modelled")
    return sorted(set(members), key=lambda m: by_object[m]["key"])


def create_stack(data: bytes, *, name: str, members: list[int], track_count: int | None = None,
                 colour: int = DEFAULT_COLOUR) -> tuple[bytes, dict]:
    """A folder stack ``name`` holding the arrange rows of ``members`` (any order)."""
    if not members:
        raise ValueError("a stack needs at least one member")
    require_full_walk(data)
    records = project_records(data)
    objs = channel_objects(data)
    chans = channels(data)
    owners_of = bound_channels(data)
    stacks = read_stacks(data, track_count)
    ordered = _members_in_order(read_tracks(data, track_count), members,
                                {s.object_id for s in stacks})
    run = arrange_run(records, track_count)
    run_rows = [records[i].raw for i in run]
    if stacks:
        pattern = max(stacks, key=lambda s: s.index)
        number, like, like_owner = pattern.index + 1, pattern.object_id, pattern.owner
        pattern_obj = object_record(records, like)
        strip_template = mixer_record(records, like_owner)
        row_template = next(raw for raw in run_rows if row_object(raw) == like)
    else:
        number, like, like_owner, pattern_obj, strip_template, row_template = _first_stack(data, records, chans)
    label = f"Sub {number}"
    if any(c.label == label for c in chans.values()):
        raise ValueError(f"{label} already exists")
    owner = like_owner + 1                            # inserted right after the pattern's strip
    object_id = next_object_id(records)
    top = max(objs)
    plan = plan_sequence(records, like=like, object_id=object_id)

    pattern_stamp = object_stamp(pattern_obj)
    new_obj = clone_object(pattern_obj, object_id=object_id, name=name, owner=owner,
                           colour=colour, icon=None, stack_number=number)
    last_env = max(i for i, r in enumerate(records) if r.tag == ENV_TAG)
    new_chan = new_sub_channel(strip_template, number=number, owner=owner, uuid=new_obj[-UUID_LEN:])
    last_like_record = max(i for i, r in enumerate(records)
                           if is_channel_record(r) and r.owner == like_owner)

    member_set = set(ordered)
    header = new_row(row_template, object_id=object_id, member=0, expanded=True)
    moved = [with_member(raw, 1) for raw in run_rows if row_object(raw) in member_set]
    at = next(k for k, raw in enumerate(run_rows) if row_object(raw) == ordered[0])
    kept = [raw for raw in run_rows if row_object(raw) not in member_set]
    new_rows = kept[:at] + [header] + moved + kept[at:]

    flat = flat_run(records, run)
    subs = [k for k, i in enumerate(flat)
            if owners_of.get(row_object(records[i].raw)) in chans
            and chans[owners_of[row_object(records[i].raw)]].label.startswith("Sub ")]
    flat_pos = max(subs) if subs else len(flat) - 1
    flat_row = clone_flat_row(records[flat[flat_pos]].raw, object_id)
    member_owners = {owners_of[m] for m in ordered if m in owners_of}
    gnos_uuid = fresh_uuid()

    out: list[bytes] = []
    run_set = set(run)
    for i, r in enumerate(records):
        if i in run_set:
            if i == run[0]:
                out += new_rows
            continue
        raw = plan.rewrite(i, r)
        oid = object_id_of(r)
        if oid is not None:
            if oid in member_set:
                raw = set_parent(raw, object_id)
            bound = owners_of.get(oid)
            raw = shifted_object(raw, channel=bound is not None and bound >= owner,
                                 stamp=object_stamp(raw) > pattern_stamp)
        elif is_mixer_record(r) and r.owner in member_owners:
            raw = set_stack_index(raw, number)
        elif is_channel_count(r):
            raw = bump_channel_count(raw, class_at=COUNT_CLASS_AT["Sub"])
        elif r.tag == GNOS_TAG:
            raw = rec(GNOS_TAG, raw, register_object(raw[HEADER:], object_id=object_id, top=top,
                                                     uuid=gnos_uuid, slot=plan.slot))
        if is_channel_record(r) and r.owner >= owner:
            raw = shifted_channel(raw, r, relabel_prefix="Sub ")
        out.append(raw)
        if i == flat[flat_pos]:
            out.append(flat_row)
        if i == plan.insert_after:
            out += plan.new
        if i == last_env:
            out.append(new_obj)
        if i == last_like_record:
            out.append(new_chan)

    result = reassemble(data, out)
    result = reassemble(result, renumbered(project_records(result)))
    result = sync_key_flags(result)                  # a cloned channel carries its pattern's flags
    result = sync_row_count(result, None if track_count is None else track_count + 1)
    result = sync_region_tracks(result, None if track_count is None else track_count + 1)
    result = select_track(result, object_id, None if track_count is None else track_count + 1)
    require_valid(result)
    return result, {"object_id": object_id, "owner": owner, "label": label,
                    "sequence": plan.index, "slot": plan.slot, "members": ordered}
