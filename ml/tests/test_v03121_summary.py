import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml

class V03121Summary(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assertIn('## Conclusion',(REPORT/'v0_3_12_1_summary.md').read_text(encoding='utf-8'))

