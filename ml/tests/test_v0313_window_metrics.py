import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_window_metrics(self): check("window_metrics")

