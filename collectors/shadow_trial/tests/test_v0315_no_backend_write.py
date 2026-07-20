from checks import unittest, verify_case

class TestV0315NoBackendWrite(unittest.TestCase):
    def test_no_backend_write(self): verify_case(self, __name__.split(".")[-1])
