import unittest,numpy as np
from v039_support import ROOT,CLASSES
from mondrian_conformal_classifier import MondrianConformalClassifier
class TestMondrian(unittest.TestCase):
 def test_training_oof_only(self):
  p=np.eye(6)[np.arange(12)%6]*.9+.1/6;y=np.array(CLASSES*2);m=MondrianConformalClassifier(.05).fit(p,y,CLASSES,source='training_oof');self.assertEqual(m.alpha,.05)
