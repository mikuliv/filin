import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_worker_order_invariance(self): check("worker_order_invariance")

