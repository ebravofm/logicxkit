# Commands

What the CLI is organised into and the rules that govern each group.

This file is about shape and safety, not flags. For a command's flags run
`logicxkit logic <command> --help`; for whether a command is trusted against a real session read
[CAPABILITIES.md](CAPABILITIES.md), which is generated from the code and cannot drift from it.

---

## Table of Contents

- [Two CLIs](#two-clis)
- [Reading a project](#reading-a-project)
- [Editing a project](#editing-a-project)
- [Building strips and presets](#building-strips-and-presets)
- [Decoding plugin state](#decoding-plugin-state)
- [Drum patterns](#drum-patterns)
- [Logic's own settings](#logics-own-settings)
- [The four rules that apply everywhere](#the-four-rules-that-apply-everywhere)
- [Adding a new command](#adding-a-new-command)

---

## Two CLIs

`logicxkit logic` works on Logic's own file formats — projects, channel strips, settings.
`logicxkit au` decodes Audio Unit plugin state, wherever it is stored.

They are separate because the dependency graph is: `au` must never import `logic`. Both read
Logic containers through `logicxkit.logicx`. `tests/test_package_layering.py` enforces this —
do not add an import that crosses it.

## Reading a project

Start here. These never write, so point them at anything.

`project` inventories a whole session — channels, chains, AU preset names, native params.
`diff` compares two projects, or one project against your strip library, which is how you find
a channel that has drifted from the `.cst` it claims to reference. `stacks`, `levels`,
`arrangement`, `tempo`, `signature`, `modes`, `metronome`, `group` and `header` each read their
own part of a session and print it. `decode` reads a `.cst` directly. `manifest` and `recdiff`
report on the record layer.

`image` extracts the window screenshot Logic auto-saves into a project, the one exception here:
it writes that JPEG (to the current directory unless `-o` says where) and keeps an existing file
unless `--overwrite` is given. `ocr` reads that screenshot with Apple Vision, which is the only way
to see the mixer as Logic actually drew it.

Several of these turn into writers when given a flag — `stacks --move`, `levels --to`. Read the
next section before using one.

## Editing a project

**Every project-mutating command requires `--out` and works on a copy. The input is never
modified.** There is no in-place mode and none will be added.

Most editors route through `_edit.edit_copy`, which holds the result against its input using
`logic/services/integrity.py` (region, file and marker checks in `integrity_regions.py`, marker
targets in order and RBA Sequences no entry names among them), refuses on any structural regression, and then reads the file
back to confirm the bytes that landed are the bytes that passed. A refused run discards the
whole copy rather than leaving a bundle that disagrees with its own metadata.

Do not assume that gate covers everything:

- **It checks structure, not sound.** It cannot tell you a chain landed on the wrong channel.
- **`chains` bypasses `edit_copy`** but runs the same regression check and read-back itself.
- **`controlbar`, `header` and `toolbar` bypass it** because they write `DisplayState.plist`
  and never touch `ProjectData`, which is what the gate inspects.
- **`retrack --map` bypasses it**: it rewrites each `ProjectData` in the copy checked only for
  an unchanged length. `retrack --channel` goes through the gate.

`apply-template` is the orchestrator over the rest: it migrates a session onto another
project's layout, pairing tracks by Environment object id within a lineage and by an explicit
map across lineages. It refuses across lineages without a map.

`migrate` runs that in one pass: it drafts the pairing with `propose-map` (or takes `--map FILE`),
applies it, and writes `CLAUDE migrated - <song>.logicx` into `--out`, never over an existing
output. A song of the template's own lineage pairs by object id and ignores the draft; any other
song is refused unless given `--map` or `--force`, and `--save-map FILE` keeps the draft to edit.
The pairing is drafted from the first alternative, which must fit or nothing is written; a
later alternative the map does not name is left as it was. A folder holding more than one
project is refused (name the song), and a refused run leaves no `--out` behind. It ends with a
checklist of refused and failed ops and session-only tracks. `--verify` is the one
command that drives Logic itself: it opens the copy, has Logic Save As it into `--out` through
`tools/driver`, closes without saving, and compares the two row lists. It needs macOS, Logic Pro
and a checkout, and refuses before writing anything when one is missing.

**Open every output in Logic before trusting it.** A green run is not confirmation; a file that
opens is not confirmation either. The way to check a writer is Save As in Logic and diff the
record list against the input.

## Building strips and presets

`build` writes `.cst` channel strips from a JSON spec, `pst` writes single-plugin settings with
no routing attached, and `verify` round-trips a spec without writing anything. `strip-save`
goes the other direction — exports a channel from a project as a `.cst`. A preset in a `build`
spec can name a `graft` instead of a `template`: the routing of one strip with the chain of
another, for a shape no saved strip has.

These are the only commands that write outside `--out`, so they carry their own gate: **a
relative `output_dir` resolves under Logic's own live library, and writing there is refused
unless you pass `--install`.** A spec cannot reach your library by omitting a key. `--overwrite`
is separately required to replace an existing file. To write elsewhere, set `output_root`, or
give an absolute `output_dir`.

`donors` writes into the data root rather than a project; `chains` reads the data root's donors
first and the package's native ones second. `retrack` repoints strip references after a library
rename — it changes a label, never a chain.

## Decoding plugin state

`au strip` is the one to reach for: it decodes the third-party plugin states embedded inside
`.cst` strips and `.logicx` projects — the layer Logic reports as a preset name and nothing
more. `au preset` does the same for a standalone preset file.

Decoding runs a ladder per state: Neural DSP and JUCE decoders first, Waves through the static
XPst table, and anything else through the headless AU host, which loads the real plugin and
reads its parameters. `--no-host` forces the static tables instead. Without a `swift` toolchain
the host is unavailable and the ladder falls back on its own.

`au params` dumps a live parameter table from an installed plugin; `au tables` lists the tables
already in the data root. `logic neural` decodes Neural DSP knob values specifically, from
either a strip or a whole project. `logic plugins` stops at identity: every slot's plug-in, and
which third-party components `auval -a` does not list on this Mac. `logic midi` reads the MIDI
regions and `--export` writes what each region plays as a Standard MIDI File with the song's tempo
map and time signatures, bar 1 at tick 0 (a split leaves both pieces holding the parent's events;
the piece plays its own span, and the `midi` and `regions` listings say `2 event(s), 1 played` when
they differ, `--json` carrying `played` beside `events`); a song with events before bar 1 is refused. `--region` and
`--note` write a region and notes on a copy through the integrity gate; a note goes into the
region on its track that holds its bar, and is refused when none or several do. The listing
numbers regions across the song (`--json` carries it as `number`), and edits take that number:
`--transpose`, `--velocity`, `--move`, `--delete` and `--quantize` change a region in place,
`--copy-region` copies one elsewhere — the whole sequence, as Logic's own copy does, so a split piece's
copy holds the parent's events too — and `--copy-notes` only the notes it plays, and `--remap [N=]SRC:DST` translates drum
note numbers between groovebin's note maps (`gm`, `addictive-drums-2`, `drum-kit-designer`) in
region N or every region on `--track`,
counting the notes with no counterpart. In-place edits run in command-line order, then
`--region`/`--note`, then the copies; a bad spec exits before anything is copied. A region number
means the same region (track, start and name) in every alternative, and is refused where an
alternative lacks it. An edit that moves an event out of its region is refused, a MIDI region
goes only onto a software instrument track, and notes at one tick are written low to high.
`--remap` keeps the pitch of chokes and stick clicks, which GM has no stroke for, and refuses a
region holding polyphonic aftertouch. `--map NAME` names each note's stroke in the listing. The
transforms are Logic's Transform window: `logic midi SONG N … --out DIR` (regions by listing number)
or `--track NAME` (every region on it) with `--select COND[,COND…]` — `position` in song bars as the
signature track numbers them, a meter change and all (a whole number is the whole bar), `pitch`, `velocity`, `length` (ticks or `1/16`), `channel`, each `=VALUE`,
`=LO-HI` or `<`, `<=`, `>`, `>=`, `!=` a value — and the operations `--set`, `--add`, `--mul`, `--min`,
`--max`, `--random`, `--flip`, `--quantize position=|length=`, `--crescendo`, `--exp` and `--reverse`
(`FIELD=VALUE`), or the presets `--humanize`, `--fixed-velocity`, `--velocity-limit`, `--random-velocity`,
`--crescendo LO..HI`, `--reverse-position`, `--reverse-pitch`, `--exp-velocity`, `--fixed-length`,
`--max-length`, `--min-length`, `--half-speed`, `--double-speed`, `--legato`, `--staccato` and `--swing`.
Consecutive operations apply in one pass reading each note as it was; each preset is its own pass,
and `--select` picks the notes once for the whole run, so a later pass works on the ones the
selection picked rather than re-picking against what an earlier pass changed. Notes outside the
selection keep their bytes, and so do the region's controller, bend and program events — half and
double speed alone move them, rescaled with the notes. A note pushed out of its region is refused as
any edit is; so is any step that moves a note's position on a region holding those events, since
they would stay behind: `position=` under `--set`, `--add`, `--mul`, `--min`, `--max`, `--random`,
`--flip`, `--crescendo` and `--quantize`, `--reverse position`, `--reverse-position`, `--swing`, and
`--humanize` unless its `pos` is 0. A region holding polyphonic aftertouch is refused as `--remap`
refuses one, half and double speed and swing take the whole region, and
`--seed N` repeats the random moves (`random` prints the seed it chose; each alternative gets the
same draws). Region numbers go before the transform flags — `--staccato 3` hands the 3 to
`--staccato`, which is refused when it leaves no region named. The arithmetic is groovebin's
(`groovebin transform` does the same to a `.mid`). `logic regions`
lists every region, numbered, with its mute, loop, fades and audio file (a split's pieces with
their first frame), and `--audio` imports a PCM WAV at the project's sample rate — other rates
are refused, since Logic converts on import and this does not. It writes onto a project with
no audio regions or with the ones Logic's own imports and splits leave, and refuses any other
layout and a WAV whose name the project already holds, before anything is copied. Names outside
ASCII are written as Logic writes them (UTF-8 region names, UTF-16 file names). The edits take
the listing number, in command-line order on a copy: `--move N=BAR`, `--trim N=BAR:BARS` (the
start with its content kept in place, the length, or both), `--split N=BAR`, `--loop N[=on|off]`,
`--mute N[=on|off]`, `--rename N=NAME`, `--fade-in N=MS[:CURVE[:speed-up]]`, `--fade-out
N=MS[:CURVE[:TYPE]]` (type `out`, `x`, `eqp` or `xs`), `--crossfade N=[MS][:CURVE[:TYPE]]` (from region
N into the one that starts inside it on its track — exactly one must; MS is the overlap when empty,
the type `eqp` by default), the inspector's `--gain N=DB`, `--delay N=TICKS`, `--transpose N=SEMITONES`,
`--fine-tune N=CENTS` and `--reverse N[=on|off]`, and `--colour N=INDEX` (a palette index; the Color
window's swatch k is 24 + k); the listing shows the parameters that are set and a colour that differs
from the track's. A looping region is not split, a flexed (quantized) region is neither trimmed nor
split, a trim past the file is refused, a MIDI region has no fades or parameters, and Transpose is
written as the entry's field alone (Logic flexes the track itself when it transposes an unflexed
region). Each edit names a region by
its number in the input's listing, whatever the imports and edits before it moved; regions
playing one sequence (aliases) take a mute each and no other edit. A number means the same region (track, name
and start) in every alternative, and is refused where an alternative lacks it — as is a marker
number (name and bar) for `logic markers`. `logic markers` lists the marker track and edits it on a copy: `--add
BAR[:BARS]:NAME`, `--rename N=NAME`, `--move N=BAR`, `--delete N`, ASCII names only. Logic's
re-save of copies carrying every region edit and every marker edit kept all of them.
`logic chains` also takes a chain keyed by a channel name instead of a strip reference — `Stereo Out`
for the main output — listing its plug-ins in slot order as declared donors with parameters named as
`services/output_params.py` names them, or by an index inside the donor's block; `config/example-mastering.json`
is the shape. A label two channels carry, a channel keyed both by strip and by name, or an index past the
block is refused before anything is written, and every configured value is read back afterwards.
`logic plugins --validate` opens each listed third-party component with `auval -v`, since the
registry keeps a component whose bundle has gone bad and Logic's own launch trusts that registry.

`logic automation` lists each track's automation lanes and points (`--json` for the raw ticks and
values; `--all` includes tracks with an empty folder). `--set "TRACK:LANE=V@BAR,..."` replaces a
lane's points on a copy (`--out`), `--copy "TRACK:LANE->TRACK"` copies a lane onto another track and
`--clear "TRACK:LANE"` empties one, the three applied in command-line order; lanes are Volume, Pan,
Mute, Solo and ±Volume (the relative lane), values 0-127 with Volume 90 and Pan 64 at unity. A parameter point whose type word carries
bit 14 is listed with a `?`: read, not decoded.

`logic sessionplayer` reads a Session Player region's settings and generated notes. `logic
patch` reads a Library patch bundle; `--build` writes one from a `.cst`, refuses a file that does
not read as a channel strip before writing anything, replaces an existing bundle with
`--overwrite` only once the new one is complete, and like `build` refuses to write into Logic's
own library without `--install`. `logic quantize-drums` quantizes a multitrack drum take on
a copy without Logic: the members of a folder stack (or `--track`s) go into a Drums group with
Editing (Selection) and Quantize-Locked (Audio), the groups named by `--off` are switched
off, Q-Reference stays on the `--ref` tracks, every member is on flex Slicing, and each
member region gets one flex marker per hit found in the reference tracks' audio with its
target on the `--grid` (4, 8, 16 or 32, the measured values; 1/16 by default). The audio is read from where the file record says,
from `Audio Files` beside the project, from the bundle's Media, or from `--audio DIR`; it may be
16/24/32-bit PCM or 32/64-bit float WAV. A song whose tempo changes, and reference audio with no
hits, are refused and nothing is written. `--bars FIRST-LAST` re-quantizes only the hits in
those song bars, on `--grid` or each region's own Quantize value, and keeps every other marker
block's bytes; regions outside the range are untouched. It refuses a region that does not start
on a line of the song's grid (quantize it whole instead), a hit whose new target would cross a kept
hit's, and an entry whose slot names a sequence other than an RBA Sequence; a region already
quantized keeps its one RBA Sequence. On a project Logic quantized itself, whose first quantize
writes the hits on the first Q-Reference region alone, a member whose list holds only the two
anchors takes that region's hits as its own (the regions must start together with the same first
frame and length), and the group is reused when every member that has audio regions is in it.
Logic's re-save of a `--bars` copy kept every marker list.

## Drum patterns

The pattern library is groovebin's: `groovebin index FOLDER --map NAME` builds an sqlite index of
any folder of `.mid` files (or of an Addictive Drums 2 `MidiDb.csv` with `--csv`), labelled from
their paths, and `groovebin search` and `groovebin show` read it. `logic beats` writes patterns
from that index into a copy of a project; `--db` names the index (default: groovebin's own, under
the user cache).

`beats place`, `compose` and `generate` write MIDI regions into a copy through the integrity gate,
each on a software instrument track only; they are DERIVED. Each tries the whole write on the
first alternative before copying, so a refusal leaves no copy. `beats place PROJECT ID --out DIR
--track NAME --bar N` lays one pattern as a region from bar N, `--repeat` times back to back,
refused at the first bar whose meter is not the pattern's; `--map NAME` translates its notes from
the map it was indexed in and `--velocity` scales every velocity. A region never grows to hold a
note: one at or past its copy's end is dropped and counted. `beats compose PROJECT --out DIR
--track NAME --group TEXT` writes one region per arrangement section whose name says Intro, Verse,
Pre-Chorus, Chorus, Bridge or Outro, from the group's patterns of that role in the section's meter
(the second verse takes the second Verse pattern, cycling), repeated to the section's length;
`--fills` puts a fill pattern's fill bar on each section's last bar. Every other section is
skipped with its reason. `beats generate PROJECT --out DIR --track NAME --bar N --meter N/D
--bars N` picks a phrase bar by bar from the index's real bars: the first starts a pattern, each
next has the kick and snare onsets nearest those of the bar that followed the last pick in its
own pattern, and timing and velocity move slightly. `--category`, `--role`, `--intensity` and
`--tempo` filter as `groovebin search` does, `--fills` puts a fill bar on every fourth bar,
`--seed` repeats a phrase (the seed used is printed) and `--map` writes it in another map;
`groovebin generate -o FILE.mid` writes the same phrase as a file for listening.

`drums-to-midi PROJECT --out DIR --hit TRACK=TERM --track TARGET` turns drum hits in audio tracks
into notes in one new MIDI region on a software instrument track, on a copy; Logic's re-save of one
kept the region and every note. Each
`--hit` names an audio track and the drum-map term its hits play (`kick`, `snare`, `hihat closed`
…) in `--map NAME` (default `addictive-drums-2`); each hit becomes a sixteenth on that key, cut at the next note on that
key, its velocity from the hit's peak scaled from the track's quietest to its loudest.
`--threshold DB` sets how far under the track's loudest hit a hit may be (lower finds quieter
hits). `--grid N` quantizes the notes first, and the region spans the whole bars holding the
quantized notes. Audio is found as `quantize-drums` finds it (`--audio DIR`); a song whose tempo
changes, an unknown term, two tracks on one key, a track with no audio regions, and a WAV whose
sample rate or own frame count disagrees with its file record are refused.

## Logic's own settings

`prefs` reads and writes Logic's application settings, which live in a plist outside any
project. It refuses to write while Logic is running and takes a backup first. This is the only
command that changes state Logic owns globally rather than per-session.

## The four rules that apply everywhere

1. **Writers take `--out` and copy first.** The input project is never modified.
2. **Logic's own library is opt-in.** `--install` to write there, `--overwrite` to replace.
3. **A command's confidence level is printed before it writes**, if that level is `CLAIMED`,
   `DERIVED` or `BROKEN`. `LOGICXKIT_NO_NOTICE=1` silences the line but not the risk.
4. **Confirmation means Logic opened it.** Not that the command exited zero.

## Adding a new command

1. Register it in the relevant `_*.py` group beside `logic/cli.py`, or in `au/cli.py`.
2. Declare its confidence level in `src/logicxkit/logic/_capabilities_table.py`.
   `tests/logic/test_capabilities.py` fails when a subcommand has no entry, so this is not
   optional.
3. Start at `DERIVED` unless you have opened the output in Logic. Raising a level needs
   evidence the level itself names — see [CAPABILITIES.md](CAPABILITIES.md).
4. If it writes a project, route it through `_edit.edit_copy` unless there is a reason not to,
   and state that reason in the capability entry's catch.
5. Add it to the right group above only if it opens a new category. A new editor does not need
   its own paragraph here; the rules already cover it.
