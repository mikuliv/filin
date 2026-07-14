import unittest
import numpy as np
from class_conditional_support import ClassConditionalSupport
class TestClassSupport(unittest.TestCase):
 def test_thresholds_and_novel(self):
  X=np.r_[np.arange(10)[:,None],(100+np.arange(10))[:,None]];y=np.array(['a']*10+['b']*10);model=ClassConditionalSupport(3,.95).fit(X,y);self.assertEqual(set(model.thresholds_),{'a','b'});self.assertEqual(model.support_sets([[1000]])[0],[])
 def test_validation_fit_blocked(self):
  with self.assertRaises(ValueError):ClassConditionalSupport().fit([[0],[1]],['a','a'],source='validation')
