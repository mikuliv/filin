import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ClassConflict(unittest.TestCase):
    def test_class_conflict(self):
        assert_case("class_conflict")
