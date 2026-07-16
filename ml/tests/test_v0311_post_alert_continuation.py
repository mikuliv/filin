import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PostAlertContinuation(unittest.TestCase):
    def test_post_alert_continuation(self):
        assert_case("post_alert_continuation")
