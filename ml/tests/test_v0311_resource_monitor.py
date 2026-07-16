import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ResourceMonitor(unittest.TestCase):
    def test_resource_monitor(self):
        assert_case("resource_monitor")
