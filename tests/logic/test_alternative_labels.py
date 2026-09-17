"""A write command's report must name the alternative each line came from.

`edit_copy` and `edit_display` run their step once per `Alternatives/*/ProjectData`, so anything
the step reports repeats once per alternative. Unlabelled, one edit on a two-alternative project
reads as two, and the printed report is all the operator gets before "Unverified until opened in
Logic." Half the commands already labelled; ten had drifted.

A step reports either by printing or by appending an f-string to a list its caller prints later —
`automation` did the second, so a detector that only looked for `print` would have missed the case
this gate exists for. Both count; a reporting step fails here until it names
`data_file.parent.name`, or `alternative.name` for the DisplayState writers.
"""

import ast
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "logicxkit" / "logic"
LABELS = (".parent.name", "alternative.name")


def reporting_calls(node: ast.FunctionDef) -> list[str]:
    """How this step puts text in front of the operator, if it does."""
    out = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Name) and n.func.id == "print":
            out.append("print")
        elif isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend"):
            if any(isinstance(a, ast.JoinedStr) for a in n.args):
                out.append(f".{n.func.attr}()")
    return out


def steps():
    """(file, line, source) for every per-alternative step closure that reports."""
    for path in sorted(SRC.rglob("*.py")):
        source = path.read_text()
        if "edit_copy" not in source and "edit_display" not in source:
            continue
        lines = source.splitlines()
        for node in ast.walk(ast.parse(source, str(path))):
            if not isinstance(node, ast.FunctionDef):
                continue
            args = [a.arg for a in node.args.args]
            if args[:2] != ["data", "count"] and args != ["alternative"]:
                continue
            if reporting_calls(node):
                yield path.name, node.lineno, "\n".join(lines[node.lineno - 1:node.end_lineno])


class AlternativeLabelTest(unittest.TestCase):
    def test_every_reporting_step_names_its_alternative(self):
        bare = [f"{name}:{line}" for name, line, body in steps()
                if not any(label in body for label in LABELS)]
        self.assertEqual(bare, [], "these report once per alternative without saying which, so one "
                                   "edit reads as several: name data_file.parent.name in the line")

    def test_the_sweep_finds_the_closures_it_screens_including_the_accumulator(self):
        """A detector that matched nothing — or only the `print` half — would pass the check above
        for the wrong reason. `automation` is the accumulator; `add-track` prints."""
        found = {name for name, _line, _body in steps()}
        self.assertGreater(len(list(steps())), 15)
        self.assertLessEqual({"_automation_cmd.py", "_apply_tracks.py"}, found)


class DetectorTest(unittest.TestCase):
    """The detector has to reject the shapes it exists to catch."""

    def calls(self, body: str) -> list[str]:
        (fn,) = ast.parse(body).body
        return reporting_calls(fn)

    def test_both_a_print_and_an_appended_f_string_read_as_reporting(self):
        self.assertEqual(self.calls('def step(data, count, f):\n    print(f"{x}")\n'), ["print"])
        self.assertEqual(self.calls('def step(data, count, f):\n    lines.append(f"{x}")\n'), [".append()"])
        self.assertEqual(self.calls('def step(data, count, f):\n    seen.append(x)\n'), [])
        self.assertEqual(self.calls('def step(data, count, f):\n    return data\n'), [])

    def test_a_bare_line_is_flagged_and_a_labelled_one_is_not(self):
        bare = 'print(f"  {track} -> {target}")'
        self.assertTrue(all(label not in bare for label in LABELS))
        for good in ('print(f"  {data_file.parent.name}: {track}")', 'print(f"  {alternative.name}: done")'):
            self.assertTrue(any(label in good for label in LABELS), good)


if __name__ == "__main__":
    unittest.main()
