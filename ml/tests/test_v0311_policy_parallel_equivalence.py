import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PolicyParallelEquivalence(unittest.TestCase):
    def test_policy_parallel_equivalence(self):
        assert_case("policy_parallel_equivalence")
