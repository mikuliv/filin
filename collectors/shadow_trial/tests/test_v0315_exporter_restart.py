from checks import unittest, verify_case

class TestV0315ExporterRestart(unittest.TestCase):
    def test_exporter_restart(self): verify_case(self, __name__.split(".")[-1])
