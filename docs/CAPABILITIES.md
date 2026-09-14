# What the Logic writers can actually do

The question this file exists to answer without a survey: **can I point this command at a real
Logic project today?**

Read the table, then the defect list, for anything you plan to run. Each row says what it was
measured against and when. All of it is macOS-only: the writers target Logic Pro's own project
format, and "confirmed" means the output was opened in Logic Pro itself.

The table is **generated from `src/logicxkit/logic/_capabilities.py`** — change a level there, not
here. `bin/run logic capabilities -v` prints it with the catch per command, and
`tests/logic/test_capabilities.py` fails when a subcommand has no entry or the two drift apart.

## Confidence levels

| Level | Means |
|---|---|
| **CONFIRMED** | Output was opened in Logic and the change was there. The save that proves it still exists. |
| **CLAIMED** | A doc says it was confirmed, but the save is gone or the code has changed since. |
| **DERIVED** | Byte layout reasoned from reads and diffs. Never opened in Logic. |
| **BROKEN** | Has a defect reproduced on a real Logic project. |

A command being in `--help` is not evidence of anything.

The controlled Logic saves these confirmations were measured against are Logic-authored project
files and are not redistributable, so a clone carries none of them; `resources/README.md` says
how to stage your own.

## The table

<!-- generated from src/logicxkit/logic/_capabilities.py — edit there, not here -->
| Command | Level | Safe on a real song? | The catch |
|---|---|---|---|
| `project` `manifest` `diff` `decode` `neural` `recdiff` | — | yes, read-only | `project`'s "channels with inserts" counts `.cst` labels, not loaded plugins |
| `plugins` | — | yes, read-only | Names every slot's plug-in — Apple's by type id, a third-party one by the AU component identity in its embedded preset — and checks the third-party ones against `auval -a`. A missing verdict has not yet been compared with Logic's own missing-plug-in dialog |
| `regions` | **CONFIRMED** | read yes; `--audio` on a copy | Every MIDI and audio region with its track and start; an audio region's file record (name, format, frames, rate, channels, bits) read from Logic's imports of two WAVs onto a blank-born project (2026-09-13). `--audio` copies a PCM WAV at the project's rate into the bundle and writes the file, region and container records held field for field to Logic's own first, second and third imports; Logic re-saved two imports written onto a blank-born project with every region record, entry and registry id as written, rewriting only each file's folder path and size, and one word of the stereo file, on load (2026-09-14). It writes onto a project with no audio regions or one whose regions are laid out as Logic's imports leave them (n file and region records numbered 0, 4, … 4(n-1), an ordinal/link chain in file order, one registry entry each), and refuses any other layout, a WAV whose name the project already holds, and other rates and formats. The track selection is not moved |
| `quantize-drums` | **CONFIRMED** | yes, on a copy | The drum-quantize procedure as file writes: groups off, the drum group with Editing (Selection) and Quantize-Locked (Audio), Q-Reference on the reference tracks, flex Slicing, and per region the two anchors plus one flex marker per hit found in the reference audio, targets on the grid, with the RBA Sequence carrying the Quantize value. Every layout is from Logic's own saves of one take (2026-09-13). Logic opened a written copy of that take reading Quantize 1/16 Note with Flex on, and its re-save kept every marker list, header, group and object field byte for byte. The hits are ours: the detector finds 78% of the transients Logic marked on that take across four grids and 88% of its own are among them, so the result is a quantize, not Logic's. The reference audio is 16/24/32-bit PCM or 32/64-bit float WAV; a song whose tempo changes and reference audio with no hits are refused |
| `sessionplayer` | — | yes, read-only | A Session Player region's settings from the JSON in its MneG record — Complexity (`rComp`), Fill Amount (`fillsAmount`) and Swing pinned by one editor move per save (2026-09-13) — with the drummer, preset and the generated notes' count. One region measured; records pair with drummer sequences in file order |
| `patch` | **CONFIRMED** | read yes; `--build` writes outside Logic's library unless `--install` | Reads a Library patch bundle in both shapes Logic writes: its nodes, each channel's settings and the plug-ins on its strip; one Logic saved from the Library reads back with all eight inserts (2026-09-13). `--build` writes the same shape from a `.cst`; a built patch installed in the user library loaded from Logic's Library with all eight inserts on the channel. A file that does not read as a channel strip, including Logic's older-format factory strips, is refused before anything is written, and `--overwrite` replaces a bundle only once the new one is complete |
| `midi` | **CONFIRMED** | read and `--export` yes; `--region`/`--note` on a copy | Notes, controllers, program changes and pitch bends read from Logic's saves of a blank project, one field changed per save (2026-09-13); the .mid is a format-1 file at the song's PPQ with its tempo map and time signatures, one track per region, and Logic imported one and saved the same events; events before bar 1 are refused. `--region` and `--note` write what Logic's Pencil click and Event List Create wrote; a region with two notes came back from Logic's re-save note for note, and so did regions named four and nine bytes long, every word after the name as written. `--note` goes into the region on its track that holds its bar and is refused when none or several do. An un-named instrument track shows its patch's name after any load |
| `stacks` | **CONFIRMED** | read-only until `--move`, which needs `--out` | Reads folder stacks and the arrange list. `--move TRACK:STACK --out DIR` writes a copy whose rows match Logic's own drag saves (2026-09-04), through the same integrity gate as every other writer |
| `levels` | **CONFIRMED** | read-only until `--to`, which needs `--out` | Reads fader and pan. `--to OTHER --out DIR` copies them onto another project through the integrity gate; a copy written onto a blank project came back from Logic's re-save with every fader and pan as written (2026-09-12) |
| `build` `verify` `pst` `donors` `image` `ocr` | — | never touches a project; `build`/`pst` reach Logic's own library only with `--install` | A relative `output_dir` resolves under `~/Music/Audio Music Apps` — Logic's own library — and writing there is refused without `--install`. `--overwrite` is separately required to replace a file. Elsewhere: `output_root` (or `strip_root` / `LOGICXKIT_STRIP_ROOT`, which moves `build`'s sources too), or an absolute `output_dir` |
| `chains` | **CONFIRMED** | yes, after reading `--plan` | Replaces a channel's whole chain. `--plan` names every chain it would take off; `--strict` refuses on shape drift. The real tracking chains written onto the tracking template came back from Logic's re-save with all 46 channels' chains identical (2026-09-12) |
| `retrack` | **CONFIRMED** | yes | Changes a label, never a chain; basename-only library match. `--channel` repoints one channel at a time, so channels sharing a name can part ways: seven repointed on a tracking template showed on the Setting buttons and survived Logic's re-save byte for byte (2026-09-06) |
| `strip-save` | **CONFIRMED** | yes |  |
| `send` | **CONFIRMED** | yes | Writes to buses the caller declared missing; no cross-project bus remap. A project with no send to clone gets Logic's own from a blank project (packaged), and Logic re-saved one such add byte for byte (2026-09-13) |
| `stack-create` | **CONFIRMED** | on a folder stack only | Summing stacks unimplemented. A session with no stack patterns on Logic's own first stack (packaged); Logic re-saved two such stacks with the header, strip and members as written (2026-09-13) |
| `add-track` | **CONFIRMED** | yes | Audio, instrument and aux adds; 46 in one migration survived Logic's own re-save row for row (2026-09-04). With no audio stub free a fresh channel is made where Logic makes one, and Logic's re-save kept three such byte for byte (2026-09-06). Keeps the song container's row count, the region placements and the registry's slot entries in step |
| `reorder` | **CONFIRMED** | yes | Moves a row among its siblings; a stack header moves with its members, and that move reproduces Logic's own drag of a header byte for byte (2026-09-12). A plain-row move came back from Logic's re-save in the written order, every row byte held but the moved row's selection mark, which Logic clears on load (2026-09-13) |
| `route` | **CONFIRMED** | yes | Sets a channel's input or output by label; an output rerouted to a bus came back from Logic's re-save with the routing intact and the channel record byte for byte (2026-09-13) |
| `arrangement` | **CONFIRMED** | yes, on a copy | Reads matched Logic's display on every project tested; a rename plus a resize survived Logic's re-save byte for byte (2026-09-06), `--add` reproduces Logic's own add record for record and survived its re-save, and a move plus a delete came back from Logic's re-save event for event. On a song with no arrangement track `--add` makes the track as Logic's first section does, and Logic re-saved one with the section intact (2026-09-13) |
| `signature` | **CONFIRMED** | yes, on a copy | Reads the signature track and the LCD's division on every project tested. `--time` at bar 1, `--key` (major and minor) and `--division` reproduce Logic's own edits byte for byte (2026-09-06/07); `--key-at` and `--time-at` add changes after bar 1 and survived Logic's re-save byte for byte. `--time` at bar 1 refuses songs with later meter changes |
| `toolbar` | **CONFIRMED** | yes, on a copy | Every button's id measured on seven saves (2026-09-07) and written in Logic's order; Logic re-saved one of ours unchanged. `--row` shows or hides the toolbar row |
| `modes` | **CONFIRMED** | yes, on a copy | Cycle, Replace, Autopunch, Metronome Click, Use Musical Grid and the count-in length in the song record, pinned on Logic's saves of one press apiece (2026-09-08); a copy written with four of them came up in Logic so and was re-saved intact. Solo is read but not copied — Logic clears it on load. `apply-template` copies them |
| `metronome` | **CONFIRMED** | yes, on a copy | The Metronome and Recording panes: nine boxes, the pre-roll time, the four Klopfgeist rows and the four MIDI click rows in the click object, pinned on Logic's saves of one change apiece (2026-09-08); a copy with six boxes and the pre-roll written, and one with changed rows copied in, each came up in Logic's pane as written and re-saved intact. `apply-template` copies them |
| `width` | **CONFIRMED** | yes, on a copy | A channel's width and the build of every plug-in on it, measured across ten sessions and a Logic-written stereo bus; two auxes made stereo on two templates came back stereo from Logic's re-save, slots included (2026-09-08) |
| `tempo` | **CONFIRMED** | yes, on a copy | Reads matched every project's LCD, ramps and steps included; `--set 180` showed 180 on Logic's LCD and survived its re-save (2026-09-06); `--add` writes the bare step Logic's Tempo List makes and survived its re-save; `--ramp` writes the event run Logic's Tempo Operations curve makes and survived its re-save event for event. Hand-drawn curves (the 0xb4 line) are read only |
| `rename` `colour` `hide` | **CONFIRMED** | yes | Applied across three legacy migrations Logic re-saved unchanged (2026-09-04); a rename marks the name as the user's, else the arrange shows the strip setting's name |
| `transplant` | **CONFIRMED** | yes, within the channel's key range | Refuses a move that overruns the slot key range — which deletes the channel's `.cst` reference record, a loss `validate_project` cannot see — and one that crosses a record class version; `--force` writes anyway. Clones take the destination's own slot keys (2 in projects whose slots start there). Two native slots moved between blank-born projects came back from Logic's re-save byte for byte (2026-09-13) |
| `bypass` | **CONFIRMED** | yes | Flips the bypass bit on the slots a channel already carries; adds nothing and removes nothing. Two bypassed slots came back from Logic's re-save with the bits as written (2026-09-13) |
| `clear-slots` | **CONFIRMED** | yes | Drops the records and their key flags; the `.cst` reference label stays. Opened in Logic with the inserts empty (2026-09-04); without the flag sync Logic refuses the file |
| `header` | **CONFIRMED** | yes | Every bit measured on seventeen single-toggle saves; a written set opened in Logic showing all sixteen components as set |
| `prefs` | **CONFIRMED** | yes, with Logic closed | Logic's own settings: 150 controls across every Settings pane pinned by single changes (General > Editing 2026-09-05, the rest 2026-09-08); a box written with Logic closed came up that way on relaunch. Not carried: Audio > Devices, Plug-in Delay Compensation, Control Surfaces (Logic's own file). Writes go through `defaults`, are refused while Logic runs, and take a backup first |
| `controlbar` | **CONFIRMED** | yes | Every id measured on fifty single-toggle saves (2026-09-04); a bar copied whole onto another project came up in Logic with that set. Both display-state files written |
| `group` | **CONFIRMED** | yes | Every box and the member events measured on twenty-eight single-change saves (2026-09-05); the writer reproduces six of Logic's saves byte for byte, and a migrated song with two groups opened in Logic showing them and re-saved with the identical group records and row list. Leaving a group: Logic's own No Group on a member (2026-09-12) matches the composed leave outside the selection bytes |
| `apply-template` | **CONFIRMED** | yes, with a map across lineages | Same lineage pairs by object id; across lineages `--map FILE` says how tracks pair (`--propose-map` drafts it, `(none)` leaves a track alone). Three legacy songs migrated onto a mixing template opened in Logic and re-saved with the identical row list (2026-09-04). Never removes a send; inputs past the session's count are made before planning (Logic re-saved six); the template's groups are made and joined by name (2026-09-05, confirmed on the same song). Legacy bus returns the template duplicates are silenced; `-` lines in the map leave template tracks out. A song whose slots start at key 2 beside three sends is moved to base 4 in the same pass, as Logic's own re-save does; a project born at base 2 without that collision is left there (`logic/README.md`: slot keys). Also carries the track power state, icons, header components and the control bar; not the project's own tempo, meter or key, which stay the song's |

**`build`/`pst` refuse Logic's own library without `--install`:** a relative `output_dir` in a
spec resolves under `~/Music/Audio Music Apps`, the channel-strip and plug-in settings libraries
Logic itself loads from, and writing there exits 2 unless `--install` is passed. An existing
file is kept unless `--overwrite` is passed. To write elsewhere, set `output_root` (moves only
the output, for both commands) or give an absolute `output_dir`; `strip_root` and
`LOGICXKIT_STRIP_ROOT` also move `build`'s output, with its sources, but not `pst`'s.

## The two rules that matter most

**1. `apply-template` pairs by object id within a lineage and by a map across one; without a map it refuses.**
`services/pairing.py` pairs on Environment object id, then mixer label, then name. Two
unrelated projects both have an `Audio 1`, so the label rule pairs them happily: on one legacy song
that meant renaming *Guitar 1* to *Kick In* and *Bass* to *Snare Up*.

`match_quality` scores the share of rows paired by object id, and the command refuses below
`LINEAGE_FLOOR` (0.5). Seven songs cut from one recording template score 1.00; three legacy
songs score 0.02 and are refused by name, with an example of what would have been
renamed. `--force` overrides, and says so loudly.

A session with a few tracks remade by hand loses only a few points, which is why the floor sits
at 0.5 rather than near 1.

**2. Every write is gated, but a gate is not an audition.** `services/integrity.py` holds
a project against the input it was given and refuses on any regression — new record-level
problems, more sequence link errors, objects whose mixer index stopped matching their channel,
channels whose send flags stopped matching their sends. It runs in `_edit.edit_copy` — the
path every `ProjectData` writer takes except `retrack --map` — and in `chains`, before the write
and again by reading the file back. A refused run discards the whole copy rather than leaving a bundle that
disagrees with its own metadata.

Proof it works: `apply-template` on a legacy song stops with `sequence link errors 0 -> 5`
rather than writing a corrupted project.

The gate covers structure, not sound. It cannot tell you a chain is on the wrong channel or
that the mix is wrong, so: **open every output in Logic before trusting it.**

## Known defects

Each of these was reproduced on a real Logic project, not inferred.

**Still open:** none. A defect reproduced on a real project goes here, with the command it
names, until a regression test closes it.
