import unittest
from v0310_alert_deduplication import AlertDeduplicator
class TestDedup(unittest.TestCase):
 def test_once_and_reset(self):
  d=AlertDeduplicator(3);self.assertIsNotNone(d.emit('a','port_scan',1,'strong'));self.assertIsNone(d.emit('a','port_scan',2,'strong'));d.reset('a');self.assertIsNotNone(d.emit('a','port_scan',2,'strong'))

