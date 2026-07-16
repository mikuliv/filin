import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311FalseDuplicateSuppression(unittest.TestCase):
    def test_false_duplicate_suppression(self):
        assert_case("false_duplicate_suppression")
