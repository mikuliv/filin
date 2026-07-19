import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(set(metric('v0310')['per_class']),set(['benign','port_scan','auth_failures','web_probe','low_rate_dos','beacon']))

if __name__ == '__main__': unittest.main()

