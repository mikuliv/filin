import tempfile,unittest
from pathlib import Path
from tools.docs.validate_v03101_summary import validate
class TestSummary(unittest.TestCase):
 def test_missing_detected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"s.md";p.write_text("# x",encoding="utf-8");self.assertFalse(validate(p)["valid"])
