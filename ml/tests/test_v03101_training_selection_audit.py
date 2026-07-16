import unittest
from ml.audits.v0_3_10_1.training_selection_audit import _close
class TestSelectionAudit(unittest.TestCase):
 def test_exact_recursive(self): self.assertTrue(_close({"a":[1,.2]},{"a":[1,.2]}))
 def test_detects_difference(self): self.assertFalse(_close({"a":1},{"a":2}))
