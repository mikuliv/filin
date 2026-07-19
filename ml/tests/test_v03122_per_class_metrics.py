import unittest

from ml.tests._v03122_support import assert_contract


class V03122PerClassMetrics(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "per_class_metrics")

