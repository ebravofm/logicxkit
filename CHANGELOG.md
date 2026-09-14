# Changelog

Notable changes to logicxkit. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [semantic versioning](https://semver.org/spec/v2.0.0.html).

## 0.3.0 — 2026-09-14

### Added

- `logic quantize-drums`: the live-drum quantize on a copy without Logic — the drum group with
  Editing (Selection) and Quantize-Locked (Audio), other groups off, Q-Reference on the
  reference tracks, flex Slicing, and one flex marker per hit found in the reference audio with
  its target on the 1/N grid (`services/onsets.py`, `flexmarkers.py`, `quantize_drums.py`).
  CONFIRMED: Logic re-saved a written take with every marker intact.
- `logic regions` reads a region's first frame within its file.
- `midi --region` and `regions --audio` place their entry correctly on a project whose regions
  carry flex markers.
- `logic regions` maps an entry to its region record by ranking the counters of every audio
  entry in every sequence, take folders included; the earlier base-offset rule mislabelled a
  project with take folders.
- `logic quantize-drums` takes a reference's audio from the file named after its region,
  handles member regions that start at different bars, and names the files it used.
- `logic project` names a native insert from its type id when the slot carries no name string,
  as `plugins` does; a built patch's eight inserts read as eight.
- The drum-quantize onset detector is tuned against the transients Logic marked across four
  grids: 78% of them found, 88% of its own among them (was 55% and 90%).
- The package carries Logic's own record templates and native plug-in donor slots, regenerated
  from the public corpus by `bin/regen_data.py`, so `add-track`, `stack-create`, `send --add`,
  `arrangement --add` and native `chains` work after `pip install` alone; a data root
  (`LOGICXKIT_DATA`) still takes precedence, and `chains` reads both donor libraries.
- `stack-create` works on a session with no stack, patterning on Logic's own first stack;
  `arrangement --add` makes the arrangement track when the song has none; `send --add` works on
  a project with no send to clone.
- `logic midi` reads a song's MIDI regions — notes, controllers, program changes, pitch bends,
  loop flag — and `--export` writes a format-1 Standard MIDI File.
- `logic plugins` names every slot's plug-in and reports which third-party components this Mac
  lacks, for one project or a folder of them.
- `logic patch` reads a Library patch bundle — its nodes, each channel's settings, strip and
  plug-ins — in both shapes Logic writes.
- The group-events loss reported on 2026-09-08 does not reproduce on the blank-born project;
  `tests/goldens/test_groups.py` pins create, assign, add, assign.
- `logic midi --region` and `--note` write an empty MIDI region and notes on a copy; Logic re-saved
  one with its notes intact.
- `logic regions` reads every MIDI and audio region with its file record (name, format, frames,
  rate, channels, bits); `--audio` imports a PCM WAV at the project's rate as a region.
- `logic sessionplayer` reads a Session Player region's drummer, preset and settings (the JSON in
  its record) and its generated notes; Complexity, Fill Amount and Swing pinned by one editor
  move per save.
- `logic patch --build` writes a patch bundle from a `.cst`, into Logic's own library only with
  `--install`; a built patch loaded from the Library with all its inserts.
- Nine more public goldens: a third send and the slot base it moves to 4, the Signature List's
  meter and key creates and edits after bar 1, and a Tempo List point and its edit.
- Sixty-two more public goldens: MIDI region writes and their re-saves, audio region writes and
  a re-save, three audio imports, a Session Player track and three settings, a Library-saved
  patch and a built one loaded.
- `tools/driver` and `tools/stage_public.py`: the accessibility driver that records goldens from
  Logic, with the recipe and the traps; CONTRIBUTING describes recording one.
- Forty-three public goldens: the arrangement track and sections, an instrument track, a track
  header click, eight native inserts, MIDI events one field per save, meter changes, and
  Logic's re-saves of route, transplant, bypass, send, stack-create, arrangement and reorder
  outputs.

### Changed

- `tempo --add` and `--ramp` write each point's time word (data +8, 1/2000 s from the SMPTE
  origin) as Logic computes it; Logic's own points and curve runs match to the digit.
- `route`, `transplant`, `bypass` and `reorder` are CONFIRMED: Logic re-saved one write of each
  with the written bytes intact.
- `logic donors` names Logic's plug-ins that ship without factory presets (Gain, EnVerb).

### Fixed

- `logic regions --audio` numbers an import as Logic's own imports do — entry word, record header
  slots, file ordinal and link chain, registry entry, current and selected marks — and refuses a
  project whose audio regions are in any other layout, or a WAV whose name it already holds,
  before anything is copied. Logic re-saved two such imports with every region record kept.
- `logic midi --note` goes into the region on the named track that holds its bar, never another
  track's region at the same tick, and is refused when no region or several hold it.
- `logic midi --region` writes a region's length and track for a name of any length; Logic
  re-saved regions named four and nine bytes long as written.
- `logic midi --export` writes the song's tempo map and time signatures, and refuses events
  before bar 1 instead of raising.
- `logic quantize-drums` reads 32/64-bit float and extensible WAVs, and refuses a song whose tempo
  changes and reference audio with no hits.
- `logic patch --build` refuses a file that is not a channel strip, leaves nothing behind when it
  fails, and replaces a bundle with `--overwrite` only once the new one is complete, exiting 1
  with the path of a replaced bundle it could not remove.
- A channel's group field is a bitmask, one bit per group: `logic group` reads a channel that
  is in several groups, or in group 3 or higher, as Logic does; `--create` keeps a member's
  other groups, `--assign` moves it out of every other one.
- `logic group` shows a switched-off group and `--group N --on/--off` sets it (flags bit 31).
- `logic regions` reads a recorded project's regions: the entry counter's base, the flex
  marker blocks after a flexed entry, and a flexed audio region's RBA sequence is not a MIDI
  region.

## 0.2.0 — 2026-09-12

### Fixed

- `validate_project` checks third-party plugin slots for duplicate keys and index collisions.
- `apply-template` places each added track after the one added just above it, so a run of new
  tracks lands in template order in one pass.
- `stacks --move` and `levels --to` write through the integrity gate; a refused result is
  discarded.
- A project writer whose step fails part-way discards the whole copy, including alternatives
  it had already written.
- `logic project` reads a channel's inserts from its plugin-slot records at slot base 2, 3 or 4;
  a plugin name in a property record, such as an aux's input source, is not an insert.
- `logic header` computes the header width from the project's own name-column width and never
  below Logic's 180-pixel floor, and says when a width grown from one stored on that floor is
  an estimate.
- `logic controlbar` keeps a project's stored button order and inserts a newly shown control
  where Logic does.
- `logic stacks` reads summing stacks (a grouping header bound to an Aux with members under
  it) as well as folder stacks; `--move` refuses a summing stack.
- `logic reorder` moves a stack header together with its members, and refuses to move a row into
  or out of a summing stack.
- `apply-template` moves a project's slot keys from base 2 to 4 only when a channel carries a
  send at key 2.
- Bar numbers given to `arrangement`, `tempo` and `signature` follow the song's time signatures.
- `logic arrangement` refuses a non-ASCII section name.
- `build` and `pst` refuse Logic's own library without `--install` whatever
  `LOGICXKIT_AUDIO_MUSIC_APPS` is set to, and refuse under the folder it names.
- `build`, `verify` and `pst` refuse a preset name that is not a plain file name.
- `logic pst` marks a failed preset `!!` and exits 1.
- `apply-template` without `--out`, `--plan` or `--propose-map` exits 2 with a message.
- A quoted `~` expands in every path argument, including lists such as `recdiff --baseline`.
- A JUCE plugin state nested past the recursion limit decodes to nothing.
- Scanning a file for embedded plists takes one parse per plist.

### Added

- `apply-template --plan` names the session tracks the template has no counterpart for.
- `chains` and `levels --to` are CONFIRMED.
- Sends read their level (`Send.level`, `Send.level_exact`).
- Leaving a group is measured against Logic's own No Group save.
- The slot base is read from the channel records' own word when they agree, and follows the
  number of sends (2, 3 or 4).
- `bin/run fetch-corpus` downloads the public golden corpus; `LOGICXKIT_REQUIRE_GOLDENS=public`
  and `LOGICXKIT_GOLDENS=owner` steer the goldens between the two corpora.
- `logic image --overwrite`; without it an existing file is kept.

## 0.1.1 — 2026-09-11

### Fixed

- The headless AU host finds `auprobe.swift` inside the installed package, so `au params` and
  state decodes use it.

### Added

- `docs/README.md` (documentation index), `docs/INSTALLATION.md` and `docs/commands.md`.
- `py.typed`: the package is annotated and now says so to type checkers.
- `aulatency.swift` is documented in `src/logicxkit/au/README.md`; it ships in the wheel and
  is run directly with `swift`.

## 0.1.0 — 2026-09-10

First public release.

### Added

- `logicxkit logic` — Logic Pro channel-strip (`.cst`) build and decode, read-only `.logicx`
  project analysis, and writers for the track list, stacks, groups, sends, routing, channel
  levels and width, arrangement, tempo, time and key signatures, transport modes, metronome,
  track headers, control bar, toolbar and Logic's own settings. Every project-mutating command
  requires `--out` and works on a copy.
- `logicxkit logic apply-template` — migrate a session onto a template, pairing by Environment
  object id within a lineage and by an explicit map across lineages.
- `logicxkit logic diff` — project-to-project and project-to-strip-library drift.
- `logicxkit logic image` / `ocr` — extract and OCR the auto-saved WindowImage via Apple Vision.
- `logicxkit au` — Audio Unit preset and state decode: FabFilter `.ffp` and `.aupreset`, Waves
  XPst, TR5 chain XML, sonible protobuf field walk, and the third-party states embedded in
  `.cst` strips and `.logicx` projects.
- Headless AU host (`auprobe.swift`) — loads an installed plugin's state and dumps every
  parameter with real names and UI-formatted values.
- `logicxkit logic capabilities` — what each command is trusted for, generated from
  `logic/_capabilities.py`.
- `logicxkit --version` (`-V`) prints the installed version.
- Write gate (`logic/services/integrity.py`): every project write is held against its input and
  refused on any regression; a refused run discards the copy.
- A write by a command whose capability level is `CLAIMED`, `DERIVED` or `BROKEN` prints a
  one-line notice naming that level (`LOGICXKIT_NO_NOTICE=1` silences it).
- `logic transplant` refuses a clone that overruns the channel's slot key range or crosses a
  record class version; `--force` overrides.
- `logic build` and `logic pst` refuse to write into Logic's own library unless `--install` is
  passed.
- Strip specs take `output_root`, which moves where built strips land without moving where
  their sources are read from.
- CI on a macOS runner; `v*` tags build an sdist + wheel, check the wheel carries the Swift
  helpers and no reference material, and publish to PyPI through a trusted publisher gated on
  reviewer approval.
