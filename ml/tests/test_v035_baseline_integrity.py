from pathlib import Path
import hashlib, unittest, yaml
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_hash(self): self.assertEqual(hashlib.sha256((R/'ml/artifacts/v0_3_3/frozen_network_sensor_v0_3_v031.joblib').read_bytes()).hexdigest(),yaml.safe_load((R/'ml/experiments/v0_3_3/frozen_model_manifest.yaml').read_text())['model_sha256'])
