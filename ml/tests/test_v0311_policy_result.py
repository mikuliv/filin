import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PolicyResult(unittest.TestCase):
    def test_policy_result(self):
        assert_case("policy_result")
