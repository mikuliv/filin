from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
BASE_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol.yaml"
REVISION_2_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r2.yaml"
REVISION_3_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r3.yaml"
REVISION_4_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r4.yaml"
REVISION_5_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r5.yaml"
REVISION_6_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r6.yaml"
PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r7.yaml"
REPORT = ROOT / "ml/reports/v0_3_17/pre_campaign_code_lock.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_files() -> list[Path]:
    files = []
    for base in (ROOT / "rehearsal", ROOT / "ml/experiments/v0_3_17"):
        files.extend(path for path in base.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    files.extend([
        ROOT / ".github/workflows/ci.yml",
        ROOT / "ml/tests/test_v0317_rehearsal.py",
        ROOT / "tools/audit/validate_v0317_bundle.py",
        ROOT / "tools/audit/validate_v0317_docs.py",
        ROOT / "tools/audit/validate_v0317_artifact_exclusion.py",
        ROOT / "docs/architecture/controlled_local_rehearsal_v0_3_17.md",
        ROOT / "docs/contracts/operator_projection_v1.md",
        ROOT / "docs/contracts/rehearsal_observability_v1.md",
        ROOT / "docs/operations/local_rehearsal_runbook.md",
        ROOT / "docs/operations/local_rehearsal_recovery_runbook.md",
    ])
    return sorted(set(files))


def main() -> int:
    from ml.experiments.v0_3_17.run_campaign import protocol as load_protocol
    protocol = load_protocol()
    image = subprocess.check_output(["docker", "image", "inspect", "filin-rehearsal-v0317:local", "--format", "{{.Id}}"], text=True).strip()
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    files = {path.relative_to(ROOT).as_posix(): sha(path) for path in source_files()}
    contracts = {
        path.relative_to(ROOT).as_posix(): sha(path)
        for path in [
            ROOT / "staging/contracts/connector_ingress_v1.schema.json",
            ROOT / "staging/contracts/connector_ingress_ack_v1.schema.json",
            ROOT / "staging/contracts/staging_event_batch_v1.schema.json",
            ROOT / "staging/contracts/receiver_batch_ack_v1.schema.json",
            ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json",
            ROOT / "rehearsal/contracts/operator_projection_v1.schema.json",
            ROOT / "rehearsal/contracts/rehearsal_observability_v1.schema.json",
        ]
    }
    value = {
        "schema_version": "v0317_pre_campaign_code_lock_v1",
        "stage": "v0.3.17",
        "git_head": git_head,
        "protocol_sha256": sha(PROTOCOL),
        "base_protocol_sha256": sha(BASE_PROTOCOL),
        "revision_2_protocol_sha256": sha(REVISION_2_PROTOCOL),
        "revision_3_protocol_sha256": sha(REVISION_3_PROTOCOL),
        "revision_4_protocol_sha256": sha(REVISION_4_PROTOCOL),
        "revision_5_protocol_sha256": sha(REVISION_5_PROTOCOL),
        "revision_6_protocol_sha256": sha(REVISION_6_PROTOCOL),
        "candidate_identity": protocol["candidate_identity"],
        "component_image_digests": {
            "filin-rehearsal-v0317:local": image,
            "python:3.11-slim": protocol["components"]["frozen_base_images"]["python_3_11_slim"],
            "zeek/zeek:7.0.5": protocol["components"]["frozen_base_images"]["zeek_7_0_5"],
        },
        "source_file_sha256": files,
        "source_tree_sha256": digest(files),
        "contract_hashes": contracts,
        "contract_tree_sha256": digest(contracts),
        "registry_hashes": {
            "candidate_registry_sha256": protocol["candidate_identity"]["registry_sha256"],
            "candidate_registry_commitment_sha256": protocol["candidate_identity"]["registry_commitment_sha256"],
        },
        "compose_sha256": sha(ROOT / "rehearsal/docker-compose.v0_3_17.yml"),
        "traffic_schedule_sha256": digest(protocol["workload_schedule"]),
        "maintenance_schedule_sha256": digest(protocol["maintenance_schedule"]),
        "fault_schedule_sha256": digest(protocol["fault_schedule"]),
        "operator_view_contract_sha256": sha(ROOT / "rehearsal/contracts/operator_projection_v1.schema.json"),
        "observability_contract_sha256": sha(ROOT / "rehearsal/contracts/rehearsal_observability_v1.schema.json"),
        "backend_tree": subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip(),
        "created_before_first_rehearsal_event": True,
        "campaign_event_count_at_lock": 0,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
