import unittest
from sklearn.model_selection import StratifiedGroupKFold
class TestNestedCV(unittest.TestCase):
 def test_design(self):self.assertEqual(StratifiedGroupKFold(n_splits=6,shuffle=True,random_state=42).n_splits,6);self.assertEqual(StratifiedGroupKFold(n_splits=4,shuffle=True,random_state=42).n_splits,4)
