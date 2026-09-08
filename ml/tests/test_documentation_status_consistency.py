from pathlib import Path
import unittest

from tools.docs.documentation_v2 import phase1_facts
from tools.docs.validate_documentation_freshness import (
    counterfactual_findings,
    stale_findings,
    lifecycle_v04_findings,
    status_semantic_findings,
    v04_facts,
    v04_stale_findings,
)
import json


ROOT = Path(__file__).resolve().parents[2]


class DocumentationStatusConsistencyTests(unittest.TestCase):
    def test_roadmap_preserves_both_track_boundaries(self):
        roadmap = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
        for marker in ("v0.3.18", "v0.3.19", "v0.4.4", "v0.4.5"):
            self.assertIn(marker, roadmap)
        self.assertIn("не реализован", roadmap)
        self.assertNotIn("sensor_ready_for_backend_integration=true", roadmap)

    def test_historical_prototypes_are_not_planned_current_capabilities(self):
        boundary = (ROOT / "docs/architecture/current-vs-historical.md").read_text(encoding="utf-8")
        self.assertIn("статический прототип MITRE", boundary)
        self.assertIn("backend/", boundary)
        self.assertIn("Исторические или демонстрационные", boundary)

    def test_stale_phase1_count_is_rejected(self):
        findings = stale_findings("Текущий план содержит 72 шаблона.", phase1_facts(ROOT))
        self.assertIn("stale_phase1_scenario_count", findings)
        self.assertIn("stale_phase1_scenario_count", stale_findings("Current Phase 1: 72 templates", phase1_facts(ROOT)))
        self.assertEqual(stale_findings("Режимы распределены по 72 шаблона.", phase1_facts(ROOT)), [])

    def test_stale_v04_state_is_rejected(self):
        text = "Последний завершённый этап v0.4.4. Следующий допустимый этап v0.4.5."
        findings = v04_stale_findings(text, v04_facts(ROOT))
        self.assertIn("stale_v04_latest_completed", findings)
        self.assertIn("stale_v04_next_allowed", findings)

    def test_old_stage_is_accepted_only_for_historical_document(self):
        text = "Последний завершённый этап v0.4.4; следующий допустимый — v0.4.5."
        facts = v04_facts(ROOT)
        self.assertTrue(lifecycle_v04_findings(text, "current", facts))
        self.assertEqual(lifecycle_v04_findings(text, "historical", facts), [])

    def test_wrong_counterfactual_source_and_count_are_rejected(self):
        artifact = json.loads((ROOT / "lab/network_validation/config/superseding_freeze_campaign.json").read_text(encoding="utf-8"))
        findings = counterfactual_findings("24 пары перечислены в technical_campaign.json", len(artifact["counterfactual_pairs"]))
        self.assertIn("wrong_counterfactual_source", findings)
        self.assertIn("counterfactual_source_missing", findings)

    def test_v4_retry_and_label_order_misuse_are_rejected(self):
        contract = json.loads((ROOT / "lab/network_validation/execution/label_vault_contract.json").read_text(encoding="utf-8"))
        status = {"independent_network_validation": {
            "package_execution_allowed_after_per_session_preflight": True,
            "historical_operational_report": {"attempt_count": 2, "retry_limit": 2},
            "label_unlock_sequence": {"contract_prerequisites": [], "then": ["scientific_metrics_calculated", "labels_unlocked"]},
        }}
        findings = status_semantic_findings(status, contract)
        self.assertIn("v4_preflight_allowed_after_retry_exhaustion", findings)
        self.assertIn("label_metrics_order_mismatch", findings)


if __name__ == "__main__":
    unittest.main()
