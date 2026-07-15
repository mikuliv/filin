import unittest
import v0310_support
from v0310_activity_key_audit import activity_state_key
class TestKey(unittest.TestCase):
 def test_stable_and_isolated(self):self.assertEqual(activity_state_key('a','1'),activity_state_key('a','1'));self.assertNotEqual(activity_state_key('a','1'),activity_state_key('b','1'))
