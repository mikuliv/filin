import unittest
import numpy as np
from mondrian_conformal_classifier import MondrianConformalClassifier
class TestMondrian(unittest.TestCase):
 def setUp(self):
  self.y=np.array(['benign']*10+['port_scan']*10);self.p=np.r_[np.tile([.9,.1],(10,1)),np.tile([.1,.9],(10,1))]
 def test_training_oof_only(self):
  with self.assertRaises(ValueError):MondrianConformalClassifier(.1).fit(self.p,self.y,['benign','port_scan'],source='validation')
 def test_deterministic_and_empty_supported(self):
  c=MondrianConformalClassifier(.1).fit(self.p,self.y,['benign','port_scan']);self.assertEqual(c.predict_set([[.5,.5]]),c.predict_set([[.5,.5]]));self.assertIsInstance(c.predict_set([[0,0]])[0],list)
