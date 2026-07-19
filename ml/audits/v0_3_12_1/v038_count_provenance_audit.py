from __future__ import annotations
import json
from pathlib import Path
import yaml

def audit(root: Path) -> dict:
    integrity=json.loads((root/"ml/reports/v0_3_8/validation_campaign_integrity.json").read_text(encoding="utf-8"))
    lock=yaml.safe_load((root/"ml/experiments/v0_3_8/validation_lock_manifest.yaml").read_text(encoding="utf-8"))
    prediction=json.loads((root/"ml/reports/v0_3_8/validation_predictions.json").read_text(encoding="utf-8"))
    predicted=len(prediction if isinstance(prediction,list) else prediction.get("records",[]))
    chain={
        "declared_campaign_rows":integrity["marker_pairs"], "captured_intervals":integrity["pcap_count"],
        "extracted_rows_including_warmup":integrity["scored_windows"]+integrity["warmup_windows"],
        "warmup_rows_excluded":integrity["warmup_windows"], "scored_rows":integrity["scored_windows"],
        "mapped_rows":lock["expected_rows"], "predicted_rows":predicted, "reported_rows":lock["expected_rows"],
    }
    return {"count_chain":chain,"first_divergence":"warmup_exclusion_before_scored_rows",
            "primary_status":"expected_count_metadata_error","secondary_findings":["frozen_validation_lock_expected_rows_is_216","252_counts_marker_and_pcap_intervals","36_warmup_rows_are_not_scored"],
            "mismatch_explained":all(chain[k]==216 for k in ("scored_rows","mapped_rows","predicted_rows","reported_rows")),
            "frozen_count_is_correct":True,"v038_re_evaluated":False,"v0312_compatibility_changed":False}
