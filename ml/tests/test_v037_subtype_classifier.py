import unittest,numpy as np
from v037_support import *
class TestSubtypeClassifier(unittest.TestCase):
 def test_low_confidence_is_unclassified(self):
  rows=metric_rows().iloc[2:3];d=decide_rows(rows,np.array([.9]),np.ones((1,5))/5,np.array([0.]),DecisionParameters(.2,.8,.35,1,'none'));self.assertEqual(d.decision_state.iloc[0],'suspicious_unclassified')
