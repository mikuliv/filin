import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ActivityKey(unittest.TestCase):
    def test_activity_key(self):
        assert_case("activity_key")
