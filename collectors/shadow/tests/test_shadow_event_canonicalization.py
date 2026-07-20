import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_event_canonicalization(self): check('event_canonicalization')
