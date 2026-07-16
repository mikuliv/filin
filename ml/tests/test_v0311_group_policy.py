import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311GroupPolicy(unittest.TestCase):
    def test_group_policy(self):
        assert_case("group_policy")
