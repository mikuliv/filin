import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_no_sensor_fallback(self): check("no_sensor_fallback")

