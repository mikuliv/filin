import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311StrongAlert(unittest.TestCase):
    def test_strong_alert(self):
        assert_case("strong_alert")
