import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'ml/analysis'))
from v035_audits import transitions
class TransitionTests(unittest.TestCase):
 def test_counts_cover_rows(self):
  import pandas as pd
  value=transitions(pd.Series(['benign','port_scan']),['port_scan','port_scan'],['benign','port_scan'])
  self.assertEqual(value['rows'],2)
