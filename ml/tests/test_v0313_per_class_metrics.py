import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_per_class_metrics(self): check("per_class_metrics")

