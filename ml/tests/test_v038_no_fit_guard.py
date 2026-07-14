import unittest
from v038_support import load_v038
NoFitGuard=load_v038('v038_no_fit_guard_unique','ml/experiments/v0_3_8/no_fit_guard.py').NoFitGuard
class TestNoFitGuard(unittest.TestCase):
 def test_all_training_operations_blocked(self):
  guard=NoFitGuard()
  for name in ('fit','fit_transform','partial_fit','calibrate','search_hyperparameters','recalibrate_conformal','refit_support','change_episode_parameters'):
   with self.assertRaises(RuntimeError):getattr(guard,name)()
  self.assertEqual(guard.partial_fit_call_count,1)
