import unittest
from pathlib import Path
from ml.tests.v0312_test_support import *

class V0312Test(unittest.TestCase):
    def test_contract(self):
        self.assertIn('## Вывод',(REPORT/'v0_3_12_summary.md').read_text(encoding='utf-8'))

if __name__ == '__main__': unittest.main()

