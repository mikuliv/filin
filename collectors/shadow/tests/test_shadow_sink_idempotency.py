import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_sink_idempotency(self): check('sink_idempotency')
