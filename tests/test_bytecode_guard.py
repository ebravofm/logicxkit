"""The stale-bytecode guard: a cache whose code differs from its source goes, a true one stays."""

import importlib.util
import py_compile
import tempfile
import unittest
from pathlib import Path

from _bytecode import purge, stale


class StaleBytecodeTest(unittest.TestCase):
    def test_a_cache_from_another_source_is_removed_and_a_true_one_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "m.py"
            src.write_text("STRIDE = 4\n")
            py_compile.compile(str(src), cfile=importlib.util.cache_from_source(str(src)), doraise=True)
            self.assertIsNone(stale(src))
            stat = src.stat()
            src.write_text("STRIDE = 5\n")                     # same size, the cache's header still matches
            import os
            os.utime(src, (stat.st_atime, stat.st_mtime))
            pyc = stale(src)
            self.assertIsNotNone(pyc)
            self.assertEqual(purge(Path(tmp)), [pyc])
            self.assertFalse(pyc.exists())
            self.assertEqual(purge(Path(tmp)), [])


class PurgedRootsTest(unittest.TestCase):
    """A stale cache under `tests` runs an old assertion, which fails exactly as invisibly as an
    old rule under `src`; both roots are swept, and both have to exist to be swept."""

    def test_both_source_roots_are_swept_and_are_real_directories(self):
        import conftest
        self.assertEqual(sorted(conftest._PURGED), ["src", "tests"])
        for name in conftest._PURGED:
            with self.subTest(name):
                self.assertTrue((conftest._ROOT / name).is_dir(), conftest._ROOT / name)


if __name__ == "__main__":
    unittest.main()
