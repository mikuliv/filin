import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        from ml.experiments.v0_3_12.read_only_benchmark_guard import HistoricalReadOnlyGuard
        import tempfile
        root=Path(tempfile.mkdtemp()); target=root/'x.txt'; target.write_text('x')
        with HistoricalReadOnlyGuard([root]) as guard:
            with self.assertRaises(PermissionError): open(target,'w')
        self.assertEqual(len(guard.blocked),1)

if __name__ == '__main__': unittest.main()

