import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_event_forbidden_fields(self): check('event_forbidden_fields')
