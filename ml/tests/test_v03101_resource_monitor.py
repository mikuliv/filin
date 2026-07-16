import tempfile,unittest,os
from pathlib import Path
from ml.performance.resource_monitor import ResourceMonitor
class TestResourceMonitor(unittest.TestCase):
 def test_sample_schema(self):
  with tempfile.TemporaryDirectory() as d:
   m=ResourceMonitor(os.getpid(),Path(d)/"trace.jsonl",.01);s=m.sample();self.assertIn("system_cpu_percent",s);self.assertIn("process_rss_mb",s)
