import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311WorkerFailure(unittest.TestCase):
    def test_worker_failure(self):
        assert_case("worker_failure")
