"""Data lookup: the data root first, the package second, a named error third."""

import os
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401
from logicxkit.utils import data


class LookupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old = os.environ.get(data.ENV)
        os.environ[data.ENV] = str(self.root)

    def tearDown(self):
        if self.old is None:
            os.environ.pop(data.ENV, None)
        else:
            os.environ[data.ENV] = self.old
        self.tmp.cleanup()

    def test_the_package_supplies_a_template_the_root_lacks(self):
        p = data.data_file("logic", "audio-channel-12.3.1.json")
        self.assertEqual(p, data.PACKAGED / "logic" / "audio-channel-12.3.1.json")
        self.assertTrue(p.is_file())

    def test_the_root_wins_when_it_has_the_file(self):
        (self.root / "logic").mkdir()
        mine = self.root / "logic" / "audio-channel-12.3.1.json"
        mine.write_text("{}")
        self.assertEqual(data.data_file("logic", "audio-channel-12.3.1.json"), mine)

    def test_a_file_neither_has_names_both_places(self):
        with self.assertRaises(data.MissingData) as e:
            data.data_file("logic", "nope.json")
        self.assertIn(str(self.root), str(e.exception))
        self.assertIn("logicxkit/data", str(e.exception))

    def test_data_dirs_lists_existing_dirs_root_first(self):
        (self.root / "donors").mkdir()
        self.assertEqual(data.data_dirs("donors"), [self.root / "donors", data.PACKAGED / "donors"])
        self.assertEqual(data.data_dirs("au"), [])          # AU tables are never packaged


class PackagingTest(unittest.TestCase):
    def test_pyproject_ships_the_data(self):
        import tomllib
        cfg = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
        self.assertIn("data/logic/*.json", cfg["tool"]["setuptools"]["package-data"]["logicxkit"])
        self.assertIn("data/donors/*", cfg["tool"]["setuptools"]["package-data"]["logicxkit"])

    def test_the_sdist_carries_every_bin_script_a_test_imports(self):
        import re
        root = Path(__file__).resolve().parents[1]
        manifest = (root / "MANIFEST.in").read_text()
        scripts = {p.stem for p in (root / "bin").glob("*.py")}
        imported = {m for f in (root / "tests").rglob("*.py") for m in re.findall(r"^import (\w+)", f.read_text(), re.M)} & scripts
        self.assertTrue(imported)
        for name in sorted(imported):
            self.assertRegex(manifest, rf"(?m)^include\b.*\bbin/{name}\.py\b", name)


class RbaTemplateTest(unittest.TestCase):
    def test_it_carries_no_take_positions(self):
        import json
        t = json.loads(data.data_file("logic", "rba-sequence-12.3.1.json").read_text())
        self.assertEqual(set(t), {"_", "qesm_header", "qesm_payload", "marker", "qsve_header", "qsve_tail", "hit"})
        self.assertEqual(bytes.fromhex(t["hit"])[:16], bytes(16))


if __name__ == "__main__":
    unittest.main()
