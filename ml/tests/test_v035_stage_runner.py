from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_no_fit(self): self.assertNotIn('.fit(', (R/'ml/experiments/v0_3_5/run_v0_3_5_stage.py').read_text())
