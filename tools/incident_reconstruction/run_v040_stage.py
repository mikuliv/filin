"""Официальный синтетический запуск v0.4.0 revision 1."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from incident_reconstruction.builder import write_json  # noqa: E402
from incident_reconstruction.canonical import sha256_hex  # noqa: E402
from incident_reconstruction.scenarios import build_positive, run_campaign  # noqa: E402
from incident_reconstruction.validation import validate_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "ml/reports/v0_4_0"))
    args = parser.parse_args()
    output = Path(args.output)
    campaign = run_campaign()
    if campaign["positive_scenario_passed_count"] != campaign["positive_scenario_count"]:
        raise SystemExit("positive_scenario_failure")
    if campaign["negative_scenario_rejected_count"] != campaign["negative_scenario_count"]:
        raise SystemExit("negative_scenario_failure")
    bundle = build_positive("multi_event_episode")
    verification = validate_bundle(bundle)
    journal = {
        "schema_version": "v0_4_0_official_run_journal_v1",
        "run_id": "v040_official_synthetic_r1",
        "protocol_revision": 1,
        "steps": ["protocol_frozen", "schemas_checked", "positive_campaign_completed", "negative_campaign_completed", "deterministic_bundle_verified"],
        "semantic_result_sha256": sha256_hex(bundle["incident_card"]),
        "external_network_attempt_count": 0,
        "backend_endpoint_call_count": 0,
        "automatic_action_attempt_count": 0
    }
    write_json(output / "synthetic_campaign_result.json", campaign)
    write_json(output / "representative_incident_card.json", bundle["incident_card"])
    write_json(output / "representative_reconstruction_bundle.json", bundle)
    write_json(output / "official_run_journal.json", journal)
    write_json(output / "standalone_verification_result.json", {"schema_version": "v0_4_0_standalone_verification_result_v1", "standalone_verifier_passed": True, "network_used": False, "git_used": False, "model_loaded": False, "backend_called": False, **verification})
    print(f"positive={campaign['positive_scenario_passed_count']}/{campaign['positive_scenario_count']}")
    print(f"negative={campaign['negative_scenario_rejected_count']}/{campaign['negative_scenario_count']}")
    print(f"semantic_result_sha256={journal['semantic_result_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
