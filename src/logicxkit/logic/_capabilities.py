"""What each command is trusted for, declared next to the code rather than in prose.

`docs/CAPABILITIES.md` is generated from this table, and `tests/logic/test_capabilities.py`
fails when the two disagree or when a subcommand has no entry, so "can I point this at a real
song?" is answered by one command rather than by reading the code.

Raising a level needs evidence, and the levels say what evidence:

    CONFIRMED  output was opened in Logic and the change was there, and the save proving it
               is staged under resources/, which the tools never write
    CLAIMED    a doc says it was confirmed, but the save is gone or the code changed since
    DERIVED    byte layout reasoned from reads and diffs; never opened in Logic
    BROKEN     has a defect reproduced on a real Logic project

The saves themselves are Logic-authored project files and are not redistributable, so a clone
carries none of them; `resources/README.md` says how to make your own. Producing any of that
evidence needs Logic Pro on macOS.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from ..utils.env import env_str

LEVELS = ("CONFIRMED", "CLAIMED", "DERIVED", "BROKEN", "—")


@dataclass(frozen=True)
class Capability:
    commands: tuple[str, ...]
    level: str
    safe: str
    catch: str = ""


CAPABILITIES = (
    Capability(("project", "manifest", "diff", "decode", "neural", "recdiff"), "—",
               "yes, read-only",
               "`project`'s \"channels with inserts\" counts `.cst` labels, not loaded plugins"),
    Capability(("plugins",), "—", "yes, read-only",
               "Names every slot's plug-in — Apple's by type id, a third-party one by the AU component "
               "identity in its embedded preset — and checks the third-party ones against `auval -a`. "
               "A missing verdict has not yet been compared with Logic's own missing-plug-in dialog"),
    Capability(("regions",), "CONFIRMED", "read yes; `--audio` on a copy",
               "Every MIDI and audio region with its track and start; an audio region's file record "
               "(name, format, frames, rate, channels, bits) read from Logic's imports of two WAVs "
               "onto a blank-born project (2026-09-13). `--audio` copies a PCM WAV at the project's "
               "rate into the bundle and writes the file, region and container records held field "
               "for field to Logic's own first, second and third imports; Logic re-saved two imports "
               "written onto a blank-born project with every region record, entry and registry id as "
               "written, rewriting only each file's folder path and size, and one word of the stereo "
               "file, on load (2026-09-14). It writes onto a project with no audio regions or one whose regions "
               "are laid out as Logic's imports leave them (n file and region records numbered 0, "
               "4, … 4(n-1), an ordinal/link chain in file order, one registry entry each), and "
               "refuses any other layout, a WAV whose name the project already holds, and other "
               "rates and formats. The track selection is not moved"),
    Capability(("quantize-drums",), "CONFIRMED", "yes, on a copy",
               "The drum-quantize procedure as file writes: groups off, the drum group with Editing "
               "(Selection) and Quantize-Locked (Audio), Q-Reference on the reference tracks, flex "
               "Slicing, and per region the two anchors plus one flex marker per hit found in the "
               "reference audio, targets on the grid, with the RBA Sequence carrying the Quantize value. "
               "Every layout is from Logic's own saves of one take (2026-09-13). Logic opened a written "
               "copy of that take reading Quantize 1/16 Note with Flex on, and its re-save kept every "
               "marker list, header, group and object field byte for byte. The hits are ours: the "
               "detector finds 78% of the transients Logic marked on that take across four grids and "
               "88% of its own are among them, so the result is a quantize, not Logic's. The "
               "reference audio is 16/24/32-bit PCM or 32/64-bit float WAV; a song whose tempo "
               "changes and reference audio with no hits are refused"),
    Capability(("sessionplayer",), "—", "yes, read-only",
               "A Session Player region's settings from the JSON in its MneG record — Complexity "
               "(`rComp`), Fill Amount (`fillsAmount`) and Swing pinned by one editor move per save "
               "(2026-09-13) — with the drummer, preset and the generated notes' count. One region "
               "measured; records pair with drummer sequences in file order"),
    Capability(("patch",), "CONFIRMED", "read yes; `--build` writes outside Logic's library unless `--install`",
               "Reads a Library patch bundle in both shapes Logic writes: its nodes, each channel's "
               "settings and the plug-ins on its strip; one Logic saved from the Library reads back "
               "with all eight inserts (2026-09-13). `--build` writes the same shape from a `.cst`; "
               "a built patch installed in the user library loaded from Logic's Library with all "
               "eight inserts on the channel. A file that does not read as a channel strip, "
               "including Logic's older-format factory strips, is refused before anything is "
               "written, and `--overwrite` replaces a bundle only once the new one is complete"),
    Capability(("midi",), "CONFIRMED", "read and `--export` yes; `--region`/`--note` on a copy",
               "Notes, controllers, program changes and pitch bends read from Logic's saves of a blank "
               "project, one field changed per save (2026-09-13); the .mid is a format-1 file at the "
               "song's PPQ with its tempo map and time signatures, one track per region, and Logic "
               "imported one and saved the same events; events before bar 1 are refused. `--region` "
               "and `--note` write what Logic's Pencil click and Event List Create wrote; a region "
               "with two notes came back from Logic's re-save note for note, and so did regions named "
               "four and nine bytes long, every word after the name as written. `--note` goes into "
               "the region on its track that holds its bar and is refused when none or several do. "
               "An un-named instrument track shows its patch's name after any load"),
    Capability(("stacks",), "CONFIRMED", "read-only until `--move`, which needs `--out`",
               "Reads folder stacks and the arrange list. `--move TRACK:STACK --out DIR` writes "
               "a copy whose rows match Logic's own drag saves (2026-09-04), through the "
               "same integrity gate as every other writer"),
    Capability(("levels",), "CONFIRMED", "read-only until `--to`, which needs `--out`",
               "Reads fader and pan. `--to OTHER --out DIR` copies them onto another project "
               "through the integrity gate; a copy written onto a blank project came back from "
               "Logic's re-save with every fader and pan as written (2026-09-12)"),
    Capability(("build", "verify", "pst", "donors", "image", "ocr"), "—",
               "never touches a project; `build`/`pst` reach Logic's own library only with "
               "`--install`",
               "A relative `output_dir` resolves under `~/Music/Audio Music Apps` — Logic's own "
               "library — and writing there is refused without `--install`. `--overwrite` is "
               "separately required to replace a file. Elsewhere: `output_root` (or `strip_root` "
               "/ `LOGICXKIT_STRIP_ROOT`, which moves `build`'s sources too), or an absolute "
               "`output_dir`"),
    Capability(("chains",), "CONFIRMED", "yes, after reading `--plan`",
               "Replaces a channel's whole chain. `--plan` names every chain it would "
               "take off; `--strict` refuses on shape drift. The real tracking chains written "
               "onto the tracking template came back from Logic's re-save with all 46 "
               "channels' chains identical (2026-09-12)"),
    Capability(("retrack",), "CONFIRMED", "yes",
               "Changes a label, never a chain; basename-only library match. `--channel` repoints one "
               "channel at a time, so channels sharing a name can part ways: seven repointed on a "
               "tracking template showed on the Setting buttons and survived Logic's re-save "
               "byte for byte (2026-09-06)"),
    Capability(("strip-save",), "CONFIRMED", "yes"),
    Capability(("send",), "CONFIRMED", "yes",
               "Writes to buses the caller declared missing; no cross-project bus remap. A project "
               "with no send to clone gets Logic's own from a blank project (packaged), and Logic "
               "re-saved one such add byte for byte (2026-09-13)"),
    Capability(("stack-create",), "CONFIRMED", "on a folder stack only",
               "Summing stacks unimplemented. A session with no stack patterns on Logic's own first "
               "stack (packaged); Logic re-saved two such stacks with the header, strip and members "
               "as written (2026-09-13)"),
    Capability(("add-track",), "CONFIRMED", "yes",
               "Audio, instrument and aux adds; 46 in one migration survived Logic's own re-save "
               "row for row (2026-09-04). With no audio stub free a fresh channel is made where "
               "Logic makes one, and Logic's re-save kept three such byte for byte (2026-09-06). "
               "Keeps the song container's row count, the region placements and the registry's "
               "slot entries in step"),
    Capability(("reorder",), "CONFIRMED", "yes",
               "Moves a row among its siblings; a stack header moves with its members, and that "
               "move reproduces Logic's own drag of a header byte for byte (2026-09-12). A plain-row "
               "move came back from Logic's re-save in the written order, every row byte held but "
               "the moved row's selection mark, which Logic clears on load (2026-09-13)"),
    Capability(("route",), "CONFIRMED", "yes",
               "Sets a channel's input or output by label; an output rerouted to a bus came back "
               "from Logic's re-save with the routing intact and the channel record byte for byte "
               "(2026-09-13)"),
    Capability(("arrangement",), "CONFIRMED", "yes, on a copy",
               "Reads matched Logic's display on every project tested; a rename plus a resize "
               "survived Logic's re-save byte for byte (2026-09-06), `--add` reproduces Logic's own "
               "add record for record and survived its re-save, and a move plus a delete came back "
               "from Logic's re-save event for event. On a song with no arrangement track `--add` "
               "makes the track as Logic's first section does, and Logic re-saved one with the "
               "section intact (2026-09-13)"),
    Capability(("signature",), "CONFIRMED", "yes, on a copy",
               "Reads the signature track and the LCD's division on every project tested. `--time` at "
               "bar 1, `--key` (major and minor) and `--division` reproduce Logic's own edits byte for "
               "byte (2026-09-06/07); `--key-at` and `--time-at` add changes after bar 1 and survived "
               "Logic's re-save byte for byte. `--time` at bar 1 refuses songs with later meter "
               "changes"),
    Capability(("toolbar",), "CONFIRMED", "yes, on a copy",
               "Every button's id measured on seven saves (2026-09-07) and written in Logic's order; "
               "Logic re-saved one of ours unchanged. `--row` shows or hides the toolbar row"),
    Capability(("modes",), "CONFIRMED", "yes, on a copy",
               "Cycle, Replace, Autopunch, Metronome Click, Use Musical Grid and the count-in length in "
               "the song record, pinned on Logic's saves of one press apiece (2026-09-08); a copy "
               "written with four of them came up in Logic so and was re-saved intact. Solo is read "
               "but not copied — Logic clears it on load. "
               "`apply-template` copies them"),
    Capability(("metronome",), "CONFIRMED", "yes, on a copy",
               "The Metronome and Recording panes: nine boxes, the pre-roll time, the four Klopfgeist "
               "rows and the four MIDI click rows in the click object, pinned on Logic's saves of one "
               "change apiece (2026-09-08); a copy with six boxes and the pre-roll written, and one "
               "with changed rows copied in, each came up in Logic's "
               "pane as written and re-saved intact. `apply-template` copies them"),
    Capability(("width",), "CONFIRMED", "yes, on a copy",
               "A channel's width and the build of every plug-in on it, measured across ten sessions "
               "and a Logic-written stereo bus; two auxes made stereo on two templates came back "
               "stereo from Logic's re-save, slots included (2026-09-08)"),
    Capability(("tempo",), "CONFIRMED", "yes, on a copy",
               "Reads matched every project's LCD, ramps and steps included; `--set 180` showed 180 on "
               "Logic's LCD and survived its re-save (2026-09-06); "
               "`--add` writes the bare step Logic's Tempo List makes and survived its re-save; "
               "`--ramp` writes the event run Logic's Tempo Operations curve makes and survived "
               "its re-save event for event. Hand-drawn curves (the 0xb4 line) are read only"),
    Capability(("rename", "colour", "hide"), "CONFIRMED", "yes",
               "Applied across three legacy migrations Logic re-saved unchanged (2026-09-04); a "
               "rename marks the name as the user's, else the arrange shows the strip setting's name"),
    Capability(("transplant",), "CONFIRMED", "yes, within the channel's key range",
               "Refuses a move that overruns the slot key range — which deletes the channel's "
               "`.cst` reference record, a loss `validate_project` cannot see — and one that "
               "crosses a record class version; `--force` writes anyway. Clones take the "
               "destination's own slot keys (2 in projects whose slots start there). Two native "
               "slots moved between blank-born projects came back from Logic's re-save byte for "
               "byte (2026-09-13)"),
    Capability(("bypass",), "CONFIRMED", "yes",
               "Flips the bypass bit on the slots a channel already carries; adds nothing and "
               "removes nothing. Two bypassed slots came back from Logic's re-save with the bits "
               "as written (2026-09-13)"),
    Capability(("clear-slots",), "CONFIRMED", "yes",
               "Drops the records and their key flags; the `.cst` reference label stays. Opened in "
               "Logic with the inserts empty (2026-09-04); without the flag sync Logic refuses the file"),
    Capability(("header",), "CONFIRMED", "yes",
               "Every bit measured on seventeen single-toggle saves; a written set opened in Logic "
               "showing all sixteen components as set"),
    Capability(("prefs",), "CONFIRMED", "yes, with Logic closed",
               "Logic's own settings: 150 controls across every Settings pane pinned by single "
               "changes (General > Editing 2026-09-05, the rest 2026-09-08); a box written with Logic "
               "closed came up that way on relaunch. Not carried: Audio > Devices, Plug-in Delay "
               "Compensation, Control Surfaces (Logic's own file). Writes go through `defaults`, are "
               "refused while Logic runs, and take a backup first"),
    Capability(("controlbar",), "CONFIRMED", "yes",
               "Every id measured on fifty single-toggle saves (2026-09-04); a bar copied whole "
               "onto another project came up in Logic with that set. Both display-state files written"),
    Capability(("group",), "CONFIRMED", "yes",
               "Every box and the member events measured on twenty-eight single-change saves "
               "(2026-09-05); the writer reproduces six of Logic's saves byte for byte, and a "
               "migrated song with two groups opened in Logic showing them and re-saved with the "
               "identical group records and row list. Leaving a group: Logic's own No Group on a member (2026-09-12) matches the composed leave outside the selection bytes"),
    Capability(("apply-template",), "CONFIRMED", "yes, with a map across lineages",
               "Same lineage pairs by object id; across lineages `--map FILE` says how tracks pair "
               "(`--propose-map` drafts it, `(none)` leaves a track alone). Three legacy songs "
               "migrated onto a mixing template opened in Logic and re-saved with the identical "
               "row list (2026-09-04). Never removes a send; inputs past the session's count are made "
               "before planning (Logic re-saved six); the template's groups are made and joined by "
               "name (2026-09-05, confirmed on the same song). Legacy bus returns the template "
               "duplicates are silenced; `-` lines in the map leave template tracks out. A song "
               "whose slots start at key 2 beside three sends is moved to base 4 in the same pass, as Logic's own re-save does; a project born at base 2 without that collision is left there "
               "(`logic/README.md`: slot keys). Also carries the track power state, icons, "
               "header components and the control bar; not the project's own tempo, meter or key, "
               "which stay the song's"),
)


NOTICE_LEVELS = ("CLAIMED", "DERIVED", "BROKEN")
NOTICE_ENV = "LOGICXKIT_NO_NOTICE"
LIBRARY_WRITERS = ("build", "pst")


def notice(cmd: str) -> str | None:
    """The one-line warning a write by `cmd` earns, or None when it earns none."""
    cap = by_command().get(cmd)
    if cap is None or cap.level not in NOTICE_LEVELS:
        return None
    return (f"logicxkit: '{cmd}' is {cap.level} — {cap.safe}. Open the result in Logic before "
            f"trusting it; `logic capabilities -v` and docs/CAPABILITIES.md say why.")


def emit_notice(args) -> None:
    """Every project-mutating command takes ``--out``, so that flag is the write signal."""
    if env_str(NOTICE_ENV):
        return
    writing = bool(getattr(args, "out", None)) or args.cmd in LIBRARY_WRITERS
    line = notice(args.cmd) if writing else None
    if line:
        print(line, file=sys.stderr)


def by_command() -> dict[str, Capability]:
    return {name: cap for cap in CAPABILITIES for name in cap.commands}


def table() -> str:
    """The markdown table `docs/CAPABILITIES.md` carries, generated."""
    rows = ["| Command | Level | Safe on a real song? | The catch |", "|---|---|---|---|"]
    for cap in CAPABILITIES:
        names = " ".join(f"`{n}`" for n in cap.commands)
        level = cap.level if cap.level == "—" else f"**{cap.level}**"
        rows.append(f"| {names} | {level} | {cap.safe} | {cap.catch} |")
    return "\n".join(rows)


def cmd_capabilities(args) -> int:
    print("What each command is trusted for. Raising a level needs evidence — see the "
          "module docstring.\n")
    width = max(len(" ".join(c.commands)) for c in CAPABILITIES)
    for cap in CAPABILITIES:
        names = " ".join(cap.commands)
        print(f"  {names:{width}s}  {cap.level:9s}  {cap.safe}")
        if cap.catch and args.verbose:
            print(f"  {'':{width}s}             {cap.catch}")
    print("\nFull detail, including the reproduced defects: docs/CAPABILITIES.md")
    return 0


def register(sub) -> None:
    ap = sub.add_parser("capabilities", help="what each command is trusted for")
    ap.add_argument("-v", "--verbose", action="store_true", help="include the catch per command")
    ap.set_defaults(func=cmd_capabilities)
