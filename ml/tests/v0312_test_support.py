from __future__ import annotations
import json, tempfile
from pathlib import Path
import numpy as np
from ml.experiments.v0_3_12.common import ROOT, read_yaml, sha256_file, sha256_json

EXP=ROOT/"ml/experiments/v0_3_12"; REPORT=ROOT/"ml/reports/v0_3_12"
def registry(): return read_yaml(EXP/"benchmark_registry.yaml")["benchmarks"]
def report(name): return json.loads((REPORT/name).read_text(encoding="utf-8"))
def policy(): return report("v0_3_12_policy_result.json")
def compatibility(): return report("feature_compatibility_matrix.json")["benchmarks"]
def metric(short): return report(f"{short}_metrics.json")
def prediction(short): return report(f"{short}_immutable_prediction.json")

