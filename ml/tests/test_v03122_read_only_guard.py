import unittest
import shutil
import tempfile
from pathlib import Path

from ml.experiments.v0_3_12_2.read_only_guard import HistoricalReadOnlyGuard
from ml.tests._v03122_support import assert_contract


class V03122ReadOnlyGuard(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "read_only_guard")

    def test_mutations_and_copy_destination_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "frozen"
            root.mkdir()
            source = Path(directory) / "source.txt"
            source.write_text("source", encoding="utf-8")
            with HistoricalReadOnlyGuard([root]) as guard:
                for operation in (
                    lambda: (root / "new.txt").write_text("x", encoding="utf-8"),
                    lambda: (root / "new-dir").mkdir(),
                    lambda: shutil.copy2(source, root / "copy.txt"),
                    lambda: root.rename(Path(directory) / "moved"),
                ):
                    with self.assertRaises(PermissionError):
                        operation()
            self.assertEqual(guard.report()["blocked_write_count"], 4)
