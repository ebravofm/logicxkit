"""`logic markers --add` spec parsing: a name may hold colons."""

import unittest

import _paths  # noqa: F401
from logicxkit.logic._edit import CommandError
from logicxkit.logic._markers_cmd import parse_add


class ParseAddTest(unittest.TestCase):
    def test_bar_bars_and_name_with_colons(self):
        self.assertEqual(parse_add("8:Bridge"), ("8", "", "Bridge"))
        self.assertEqual(parse_add("8:2:Bridge"), ("8", "2", "Bridge"))
        self.assertEqual(parse_add("8:Chorus: take 2"), ("8", "", "Chorus: take 2"))
        self.assertEqual(parse_add("8.5:2:A: B"), ("8.5", "2", "A: B"))
        self.assertEqual(parse_add("8:2:"), ("8", "", "2:"))
        for bad in ("8", "x:Name", ":Name", "8:"):
            with self.subTest(bad), self.assertRaises(CommandError):
                parse_add(bad)


if __name__ == "__main__":
    unittest.main()
