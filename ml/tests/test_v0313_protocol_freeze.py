import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_protocol_freeze(self): check("protocol_freeze")

