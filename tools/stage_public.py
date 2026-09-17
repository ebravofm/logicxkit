"""Stage Logic saves from out/scratch into tests/corpus/ and the tracked public manifest.

    python3 tools/stage_public.py spec.json

spec: [{"save": "<bundle name under out/scratch>", "name": "<public bundle name>",
        "key": "<manifest key>", "note": "...", "facts": {...}}, ...]
One alternative per save, without its WindowImage or Autosave; Resources/ProjectInformation.plist
kept. A save is refused unless every project title in it carries the neutral prefix, and a name,
key or note is refused when it holds a word of `LOGICXKIT_PRIVATE_WORDS` (the environment or `.env`).
"""
import json
import os
import plistlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH, CORPUS, MANIFEST = ROOT / "out/scratch", ROOT / "tests/corpus", ROOT / "tests/goldens/manifest.json"
NEUTRAL = ("CLAUDE ", "{PROJECT_NAME}")
SKIP = shutil.ignore_patterns("WindowImage*", "Autosave*")


def private_words() -> list[str]:
    raw = os.environ.get("LOGICXKIT_PRIVATE_WORDS")
    if raw is None:
        env = ROOT / ".env"
        for line in env.read_text().splitlines() if env.exists() else []:
            if line.startswith("LOGICXKIT_PRIVATE_WORDS="):
                raw = line.partition("=")[2].strip().strip("'\"")
    return [w.strip() for w in (raw or "").split(",") if w.strip()]


def leaks(text: str, words: list[str]) -> list[str]:
    """Words found in ``text``, case and separators aside."""
    return [w for w in words
            if re.search(r"[^A-Za-z0-9]*".join(re.escape(t) for t in re.split(r"[^A-Za-z0-9]+", w) if t), text, re.I)]


def titles(bundle: Path) -> list[str]:
    """The project title of every alternative: ``VariantNames`` is a dict keyed by alternative."""
    with (bundle / "Resources/ProjectInformation.plist").open("rb") as f:
        names = plistlib.load(f).get("VariantNames", {})
    return [str(t) for t in (names.values() if isinstance(names, dict) else names)]


def unneutral(bundle: Path) -> list[str]:
    return [t for t in titles(bundle) if not (t.startswith(NEUTRAL[0]) or t == NEUTRAL[1])]


def refuse(item: dict, why: str) -> None:
    sys.exit(f"REFUSED {item['save']!r}: {why}")


def main(spec_path: Path) -> int:
    words = private_words()
    spec = json.loads(spec_path.read_text())
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        "_about": "Public goldens: Logic's own saves of a blank project, one change per save, tracked "
                  "under tests/corpus/. Paths are relative to that directory. Facts are what tests may assert."}
    for item in spec:
        src = SCRATCH / item["save"]
        if bad := unneutral(src):
            refuse(item, f"project title(s) {bad} lack the neutral prefix; Save As under a 'CLAUDE …' name first")
        for field in ("name", "key", "note"):
            if hit := leaks(str(item.get(field, "")), words):
                refuse(item, f"{field} carries a private word: {hit}")
        alt = sorted(src.glob("Alternatives/*"))[0]
        dst = CORPUS / item["name"]
        if dst.exists():
            shutil.rmtree(dst)
        (dst / "Alternatives").mkdir(parents=True)
        shutil.copytree(alt, dst / "Alternatives" / alt.name, ignore=SKIP)
        (dst / "Resources").mkdir()
        shutil.copy2(src / "Resources/ProjectInformation.plist", dst / "Resources/ProjectInformation.plist")
        manifest[item["key"]] = {"path": item["name"], "note": item["note"], "facts": item.get("facts", {})}
        print(f"  {item['key']:34s} <- {item['save']}")
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(spec)} staged; manifest has {len(manifest) - 1} keys")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
