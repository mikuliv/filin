import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        from ml.experiments.v0_3_12.no_fit_guard import NoFitGuard
        from sklearn.ensemble import HistGradientBoostingClassifier
        with NoFitGuard() as guard:
            with self.assertRaises(RuntimeError): HistGradientBoostingClassifier().fit([[0],[1]],[0,1])
        self.assertEqual(guard.counters['fit_call_count'],1)

if __name__ == '__main__': unittest.main()

