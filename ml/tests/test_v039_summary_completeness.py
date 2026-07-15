import tempfile,unittest
from pathlib import Path
from v039_support import ROOT
from tools.docs.validate_v039_summary import validate
class TestSummary(unittest.TestCase):
 def test_placeholder_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'s.md';p.write_text('# x\n\nРезультаты зафиксированы в одноимённом JSON-отчёте',encoding='utf8');self.assertTrue(validate(p))
