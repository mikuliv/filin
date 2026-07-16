import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311GroupedFolds(unittest.TestCase):
    def test_grouped_folds(self):
        assert_case("grouped_folds")
