import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311DuplicateSuppression(unittest.TestCase):
    def test_duplicate_suppression(self):
        assert_case("duplicate_suppression")
