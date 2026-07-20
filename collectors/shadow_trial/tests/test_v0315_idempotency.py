from checks import unittest, verify_case

class TestV0315Idempotency(unittest.TestCase):
    def test_idempotency(self): verify_case(self, __name__.split(".")[-1])
