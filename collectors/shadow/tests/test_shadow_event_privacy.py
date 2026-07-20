import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_event_privacy(self): check('event_privacy')
