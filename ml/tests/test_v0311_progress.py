import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311Progress(unittest.TestCase):
    def test_progress(self):
        assert_case("progress")
