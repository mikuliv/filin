import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ClosedSetPolicy(unittest.TestCase):
    def test_closed_set_policy(self):
        assert_case("closed_set_policy")
