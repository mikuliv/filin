import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311Mapping(unittest.TestCase):
    def test_mapping(self):
        assert_case("mapping")
