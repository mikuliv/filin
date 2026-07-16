import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def load(relative): return json.loads((ROOT/relative).read_text(encoding="utf-8"))
def semantics():
    from ml.audits.v0_3_10_1.pending_semantics_audit import reconstruct
    return reconstruct(load("ml/reports/v0_3_10/decision_transitions.json")["records"],load("ml/reports/v0_3_10/validation_predictions.json"))[0]
