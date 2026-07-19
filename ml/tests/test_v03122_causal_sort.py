import unittest

from ml.tests._v03122_support import assert_contract


class V03122CausalSort(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "causal_sort")

