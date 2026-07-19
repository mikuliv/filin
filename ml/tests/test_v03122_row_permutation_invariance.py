import unittest

from ml.tests._v03122_support import assert_contract


class V03122RowPermutationInvariance(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "row_permutation_invariance")

