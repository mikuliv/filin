from checks import unittest, verify_case

class TestV0315RowIdentity(unittest.TestCase):
    def test_row_identity(self): verify_case(self, __name__.split(".")[-1])
