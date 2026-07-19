import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_capture_hashes(self): check("capture_hashes")

