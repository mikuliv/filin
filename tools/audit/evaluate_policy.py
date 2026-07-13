"""Evaluate a future policy against non-sensitive JSON evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ml.policy.policy_gate import evaluate_policy
from tools.audit.integrity_evidence import IntegrityEvidence


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--policy", required=True); parser.add_argument("--evidence", required=True)
    args = parser.parse_args(); policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8")); raw = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    integrity = {key: IntegrityEvidence(key, value["status"], value["reason"], value.get("evidence", {})) for key, value in raw.get("integrity", {}).items()}
    print(json.dumps(evaluate_policy(policy, raw, integrity), ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
