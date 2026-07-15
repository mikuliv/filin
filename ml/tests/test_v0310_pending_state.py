import unittest
from v0310_pending_state import PendingState
class TestPending(unittest.TestCase):
 def test_ttl_reset(self):
  s=PendingState(2,'two_of_three');s.add('a','port_scan',1,.5,.1);s.expire('a',3);self.assertFalse(s.confirmed_classes('a',3))

