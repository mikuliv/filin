from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]


class V033CampaignSchemaTests(unittest.TestCase):
    def test_campaign_has_twelve_runs_and_expected_support(self):
        campaign = yaml.safe_load((ROOT / "lab/campaigns/v0_3_3_environment.yaml").read_text(encoding="utf-8"))
        self.assertEqual(campaign["campaign_id"], "filin-v0.3.3-environment")
        self.assertEqual(len(campaign["runs"]), 12)
        self.assertEqual({run["group"] for run in campaign["runs"]}, {"mixed", "hard_negative", "degraded", "tls_proxy"})
        self.assertEqual(len(campaign["execution_catalog"]["benign"]), 12)
        self.assertEqual(len(campaign["execution_catalog"]["attacks"]), 5)
