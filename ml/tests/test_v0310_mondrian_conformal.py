import unittest
from mondrian_conformal_classifier import MondrianConformalClassifier
class TestMondrian(unittest.TestCase):
 def test_alpha(self):self.assertEqual(MondrianConformalClassifier(.05).alpha,.05)

