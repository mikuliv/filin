import unittest,numpy as np
from v037_support import *
class TestAbstention(unittest.TestCase):
 def test_uncertain_gate_is_insufficient(self):
  rows=metric_rows().iloc[:1];d=decide_rows(rows,np.array([.5]),np.ones((1,5))/5,np.array([0.]),DecisionParameters(.2,.8,.35,1,'none'));self.assertEqual(d.decision_state.iloc[0],'insufficient_evidence')
 def test_ood_does_not_become_attack(self):
  rows=metric_rows().iloc[2:3];d=decide_rows(rows,np.array([.9]),np.eye(5)[:1],np.array([2.]),DecisionParameters(.2,.8,.35,1,'none'));self.assertEqual(d.decision_state.iloc[0],'insufficient_evidence')
