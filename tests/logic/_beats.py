"""A synthetic groovebin library for the beats tests: .mid files built here and indexed from a
folder, so no library file and no MidiDb.csv is needed."""

from pathlib import Path

from groovebin.events import Event, Note
from groovebin.library.index import build
from groovebin.library.search import get, search
from groovebin.midi import write
from groovebin.song import Part, Song

BAR = 3840
KICK, SNARE, HAT, TOM, STICKS = 0x24, 0x26, 0x31, 0x47, 0x4B
GROUP = "Test Kit"
MAP = "addictive-drums-2"


def pattern_file(ppq: int, notes: list[tuple[int, int, int, int]], meter: tuple[int, int] | None = (4, 4)) -> bytes:
    """A format-0 file of ``(tick, pitch, velocity, length)`` notes on channel 10."""
    events = () if meter is None else (Event(0, bytes([0xFF, 0x58, 4, meter[0], meter[1].bit_length() - 1, 24, 8])),)
    return write(Song(ppq, 0, (Part(ppq, tuple(Note(t, length, 10, p, v) for t, p, v, length in notes), events),)))


INTRO = pattern_file(240, [(0, KICK, 100, 120), (480, SNARE, 90, 60), (960, KICK, 100, 120), (1440, SNARE, 110, 60)])
VERSE_1 = pattern_file(480, [(0, KICK, 100, 240), (0, HAT, 70, 120), (960, SNARE, 96, 120), (1440, HAT, 60, 120)])
VERSE_2 = pattern_file(960, [(0, KICK, 120, 240), (1920, SNARE, 100, 240), (2880, STICKS, 50, 60)])
FILL = pattern_file(240, [(0, KICK, 127, 120), (960, TOM, 90, 60), (1200, TOM, 100, 60), (1440, SNARE, 120, 60)])
WALTZ = pattern_file(240, [(0, KICK, 100, 120), (240, HAT, 60, 60), (480, HAT, 60, 60)], (3, 4))
TAIL = pattern_file(9600, [(0, KICK, 100, 2400), (38399, SNARE, 80, 3)])

FILES = {f"Rock/{GROUP}/Intro.mid": INTRO, f"Rock/{GROUP}/Verse 02.mid": VERSE_2, f"Rock/{GROUP}/Verse 01.mid": VERSE_1,
         f"Rock/{GROUP}/Fills 01.mid": FILL, f"Rock/{GROUP}/Chorus.mid": WALTZ, f"Rock/{GROUP} Two/Verse.mid": VERSE_1,
         "Rock/Tails/tail.mid": TAIL}


def index(folder: Path, files: dict[str, bytes] = FILES) -> Path:
    """The files under ``folder/library`` (the first folder is the category, the second the
    group, the stem the variant with its role) indexed in the Addictive Drums 2 map."""
    root = folder / "library"
    for name, data in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(data)
    db = folder / "library.sqlite"
    build(db, folder=root, map_name=MAP)
    return db


def beat(db: Path, variant: str, group: str = GROUP) -> dict:
    (hit,) = [r for r in search(db, group=group, limit=None) if r["group_name"] == group and r["variant"] == variant]
    return get(db, hit["id"])
