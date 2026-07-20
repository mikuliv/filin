import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_queue_priority(self): check('queue_priority')
