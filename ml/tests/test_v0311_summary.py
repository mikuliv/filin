import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311Summary(unittest.TestCase):
    def test_summary(self):
        assert_case("summary")
