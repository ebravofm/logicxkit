"""`logic migrate` held to Logic's re-save of a migrated legacy session."""

import unittest

import _goldens
from logicxkit.logic.services.project import project_metadata
from logicxkit.logic.services.stacks import read_tracks
from logicxkit.logic.services.validate import validate_project
from logicxkit.logicx import project_data


@_goldens.needs("legacy-migrate-mine", "legacy-migrate-logic")
class LogicResavedTest(unittest.TestCase):
    def test_logic_kept_every_row_of_the_migrated_session(self):
        want = _goldens.fact("legacy-migrate-mine", "rows")
        self.assertEqual(len(want), 57)
        for key in ("legacy-migrate-mine", "legacy-migrate-logic"):
            path = _goldens.path(key)
            data, count = project_data(path), project_metadata(path).get("tracks")
            self.assertEqual(validate_project(data), [])
            self.assertEqual([[t["name"], t.get("label")] for t in read_tracks(data, count)], want)


if __name__ == "__main__":
    unittest.main()
