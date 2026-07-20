import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_event_hash_chain(self): check('event_hash_chain')
