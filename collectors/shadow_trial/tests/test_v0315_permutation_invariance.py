from checks import unittest, verify_case

class TestV0315PermutationInvariance(unittest.TestCase):
    def test_permutation_invariance(self): verify_case(self, __name__.split(".")[-1])
