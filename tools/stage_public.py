"""Stage Logic saves from out/scratch into resources/public/ and the tracked public manifest.

    python3 tools/stage_public.py spec.json

spec: [{"save": "<bundle name under out/scratch>", "name": "<public bundle name>",
        "key": "<manifest key>", "note": "...", "facts": {...}}, ...]
One alternative per save, without its WindowImage; Resources/ProjectInformation.plist kept.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH, PUBLIC, MANIFEST = ROOT / "out/scratch", ROOT / "resources/public", ROOT / "tests/goldens/manifest.json"

spec = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
    "_about": "Public goldens: Logic's own saves of a blank project, one change per save. Paths are "
              "relative to resources/; bin/run fetch-corpus puts the files there. Facts are what tests may assert."}
for item in spec:
    src = SCRATCH / item["save"]
    alt = sorted(src.glob("Alternatives/*"))[0]
    dst = PUBLIC / item["name"]
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "Alternatives").mkdir(parents=True)
    shutil.copytree(alt, dst / "Alternatives" / alt.name, ignore=shutil.ignore_patterns("WindowImage*"))
    (dst / "Resources").mkdir()
    shutil.copy2(src / "Resources/ProjectInformation.plist", dst / "Resources/ProjectInformation.plist")
    manifest[item["key"]] = {"path": f"public/{item['name']}", "note": item["note"], "facts": item.get("facts", {})}
    print(f"  {item['key']:34s} <- {item['save']}")
MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
print(f"{len(spec)} staged; manifest has {len(manifest) - 1} keys")
