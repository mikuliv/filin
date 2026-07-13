import unittest
from ml.tests.v036_test_utils import ROOT
class AttackVariantTests(unittest.TestCase):
 def test_only_five_safe_classes(self):
  text=(ROOT/'lab/docker/services/traffic-client/client.py').read_text(encoding='utf-8')
  for name in ('attack_port_scan','attack_auth_failures','attack_web_probe','attack_low_rate_dos','attack_beacon_simulation'):self.assertIn(name,text)
  self.assertNotIn('subprocess.run(["nmap"',text);self.assertNotIn('masscan ',text)
