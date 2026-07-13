import unittest,numpy as np
from v037_support import *
class TestHierarchicalGate(unittest.TestCase):
 def test_benign_gate_never_returns_attack(self):
  rows=metric_rows().iloc[:1];d=decide_rows(rows,np.array([.1]),np.ones((1,5))/5,np.array([0.]),DecisionParameters(.2,.8,.35,1,'none'));self.assertEqual(d.decision_state.iloc[0],'benign')
