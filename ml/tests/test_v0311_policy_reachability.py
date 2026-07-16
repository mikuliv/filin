import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PolicyReachability(unittest.TestCase):
    def test_policy_reachability(self):
        assert_case("policy_reachability")
