import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ClassPolicy(unittest.TestCase):
    def test_class_policy(self):
        assert_case("class_policy")
