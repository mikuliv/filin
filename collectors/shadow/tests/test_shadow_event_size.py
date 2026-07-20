import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_event_size(self): check('event_size')
