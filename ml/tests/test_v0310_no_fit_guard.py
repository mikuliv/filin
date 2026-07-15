import unittest
from no_fit_guard import BLOCKED
class TestNoFit(unittest.TestCase):
 def test_blocks(self):self.assertIn('fit',BLOCKED);self.assertIn('modify_validation_lock',BLOCKED)

