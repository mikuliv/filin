import unittest,numpy as np
from v039_support import ROOT
from continuous_class_support import ContinuousClassSupport
class TestSupport(unittest.TestCase):
 def test_margins_and_validation_block(self):
  X=np.arange(72,dtype=float).reshape(24,3);y=np.array(['a']*12+['b']*12);m=ContinuousClassSupport(3,.975).fit(X,y,source='training_oof');r=m.transform(X[:1])[0];self.assertEqual(sorted(r.ranks.values()),[1,2]);self.assertRaises(ValueError,ContinuousClassSupport().fit,X,y,source='validation')
