import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311NoFit(unittest.TestCase):
    def test_no_fit(self):
        assert_case("no_fit")
