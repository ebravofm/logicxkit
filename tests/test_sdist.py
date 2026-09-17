"""The sdist carries only what MANIFEST.in names: nothing gitignored under docs/ or config/, no
corpus, no golden tests, and no path of a real machine. The leak gate reads the git index, so this
is the only check that sees the archive itself. Skips without the `build` package."""

import importlib.util
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from _paths import REPO

FORBIDDEN_DIRS = ("docs/pf-core/", "config/local/", "tests/corpus/", "tests/goldens/")
# Built from parts so this file's own text carries none of them.
PATH_SHAPES = tuple("/".join(p) for p in (("", "Users", ""), ("~", "projects", ""), ("", "Volumes", "")))
# The guard test names Logic's library paths on purpose; the gate exempts it the same way.
SHAPE_EXEMPT = ("tests/test_no_live_library.py",)


@unittest.skipUnless(importlib.util.find_spec("build"), "the build package is not installed")
class SdistTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        run = subprocess.run([sys.executable, "-m", "build", "--sdist", "--outdir", cls.tmp.name, str(REPO)],
                             capture_output=True, text=True, cwd=REPO)
        if run.returncode != 0:
            raise unittest.SkipTest("the sdist could not be built here:\n" + run.stderr[-1500:])
        (archive,) = Path(cls.tmp.name).glob("*.tar.gz")
        with tarfile.open(archive) as tar:
            cls.members = {m.name.split("/", 1)[1]: tar.extractfile(m).read()
                           for m in tar.getmembers() if "/" in m.name and m.isfile()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_shipped_file_is_tracked_by_git(self):
        """`recursive-include tests *.py` would take an untracked scratch file along; git's index is
        the list of what may ship."""
        run = subprocess.run(["git", "ls-files", "-z"], capture_output=True, cwd=REPO)
        tracked = set(run.stdout.decode().split("\0"))
        generated = ("PKG-INFO", "setup.cfg")
        untracked = sorted(n for n in self.members
                           if n and n not in tracked and not n.endswith(generated) and ".egg-info/" not in n)
        self.assertEqual(untracked, [])

    def test_nothing_gitignored_or_golden_ships(self):
        for prefix in FORBIDDEN_DIRS:
            with self.subTest(prefix):
                self.assertEqual([n for n in self.members if n.startswith(prefix)], [])

    def test_the_named_files_ship(self):
        for name in ("docs/CAPABILITIES.md", "docs/commands.md", "config/example-mastering.json",
                     "tests/conftest.py", "tests/_goldens.py", "CHANGELOG.md"):
            with self.subTest(name):
                self.assertIn(name, self.members)

    def test_no_text_member_names_a_real_path(self):
        for name, raw in self.members.items():
            if name in SHAPE_EXEMPT:
                continue
            try:
                text = raw.decode()
            except UnicodeDecodeError:
                continue
            for shape in PATH_SHAPES:
                with self.subTest(name, shape=shape):
                    self.assertNotIn(shape, text)


if __name__ == "__main__":
    unittest.main()
