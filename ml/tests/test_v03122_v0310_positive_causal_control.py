import unittest

from ml.tests._v03122_support import assert_contract


class V03122V0310PositiveCausalControl(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "v0310_positive_causal_control")

