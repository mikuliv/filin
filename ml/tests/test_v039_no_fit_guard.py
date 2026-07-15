import unittest
from v039_support import ROOT
from no_fit_guard import BLOCKED
class TestNoFit(unittest.TestCase):
 def test_all_training_operations(self):self.assertTrue({'fit','partial_fit','decision_grid_evaluate','lifecycle_tune'}<=set(BLOCKED))
