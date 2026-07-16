import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311StagedSelection(unittest.TestCase):
    def test_staged_selection(self):
        assert_case("staged_selection")
