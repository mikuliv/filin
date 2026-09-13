from __future__ import annotations

import json
import os

import pytest

from lab.vnext.labctl import MATRIX, SEQUENCES, docker_available, down, run_matrix, run_multi_window_sequences, up


pytestmark = pytest.mark.docker_integration

def test_real_docker_pcap_zeek_pipeline() -> None:
    if os.environ.get("FILIN_RUN_DOCKER_INTEGRATION") != "1":
        pytest.skip("Docker integration отключён; задайте FILIN_RUN_DOCKER_INTEGRATION=1")
    available, reason = docker_available()
    if not available:
        pytest.skip(f"Docker недоступен: {reason}")
    try:
        up()
        campaign_dir = run_matrix()
        summary = json.loads((campaign_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary["scenario_count"] == len(MATRIX) >= 10
        assert set(summary["a_b_comparisons"]) == {"recon", "credential", "beacon"}
        manifests = list(campaign_dir.glob("*/manifest.json"))
        assert len(manifests) == len(MATRIX)
        for manifest_path in manifests:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["pcap_sha256"]
            assert "conn.log" in manifest["zeek_log_digests"]
            assert manifest["event_counts"]["network.flow"] > 0
            assert manifest["feature_group_status"]["legacy_network_v2"] == "AVAILABLE"
            assert manifest["observation_bundle_digest"]
            assert manifest["feature_bundle_digest"]
            assert manifest["detection_result_digest"]
        sequence_dir = run_multi_window_sequences()
        sequence_summary = json.loads((sequence_dir / "multi-window-summary.json").read_text(encoding="utf-8"))
        assert sequence_summary["sequence_count"] == len(SEQUENCES) == 5
        for sequence in sequence_summary["sequences"]:
            assert len(sequence["pcap_sha256"]) == 2
            assert sequence["graph_digest"] and sequence["reasoning_graph_digest"]
            assert sequence["correlation_digest"] and sequence["incident_digest"]
    finally:
        down()
