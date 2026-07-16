import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ThreadLimits(unittest.TestCase):
    def test_thread_limits(self):
        assert_case("thread_limits")
