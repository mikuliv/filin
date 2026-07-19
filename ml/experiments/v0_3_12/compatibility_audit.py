from __future__ import annotations
import csv, math
from pathlib import Path
from .common import ROOT, read_yaml, sha256_file, sha256_json, source_metadata

def audit_benchmark(item: dict, feature_order: list[str]) -> dict:
    reasons=[]; path=ROOT/item["feature_table_path"] if item.get("feature_table_path") else None
    actual_rows=0; matrix_hash=None; feature_count=0; values_finite=False
    if path is None or not path.exists(): reasons.append("blocked_missing_frozen_features")
    else:
        with path.open(encoding="utf-8",newline="") as stream:
            reader=csv.DictReader(stream); names=reader.fieldnames or []; feature_count=len(names)
            missing=[x for x in feature_order if x not in names]
            if missing: reasons.append("missing_features:"+",".join(missing))
            if len(names)!=len(set(names)): reasons.append("duplicate_feature_names")
            digest_rows=[]; finite=True
            for row in reader:
                actual_rows+=1
                try: vals=[float(row[x]) for x in feature_order]
                except (KeyError,ValueError): vals=[]; finite=False
                if vals and not all(math.isfinite(x) for x in vals): finite=False
                digest_rows.append(vals)
            values_finite=finite
            if not finite: reasons.append("non_finite_values")
            matrix_hash=sha256_json({"benchmark_id":item["benchmark_id"],"ordered_feature_names":feature_order,"rows":digest_rows,"dtypes":["float64"]*len(feature_order),"missing_value_mask":[]})
    if actual_rows and actual_rows!=item["expected_scored_row_count"]: reasons.append(f"row_count_mismatch:{actual_rows}!={item['expected_scored_row_count']}")
    lock=read_yaml(ROOT/item["validation_lock_path"]) if item.get("validation_lock_path") and (ROOT/item["validation_lock_path"]).exists() else {}
    run_count=len(lock.get("run_ids",[]))
    if run_count and run_count!=item["expected_run_count"]: reasons.append(f"run_count_mismatch:{run_count}!={item['expected_run_count']}")
    has_mapping=bool(lock.get("dataset_paths"))
    has_episode=bool(lock.get("episode_mapping_sha256"))
    mode="incompatible" if reasons else ("full_stateful" if has_mapping and has_episode else "stateful_without_episode_mapping" if has_mapping else "window_only")
    return {"benchmark_id":item["benchmark_id"],"compatibility_status":mode,"evaluation_mode":mode,"blocking_reasons":reasons,"actual_run_count":run_count,"actual_scored_row_count":actual_rows,"actual_episode_count":item.get("expected_episode_count") if has_episode else None,"feature_count":feature_count,"all_values_finite":values_finite,"feature_table_sha256":sha256_file(path) if path and path.exists() else None,"canonical_feature_matrix_sha256":matrix_hash,"run_mapping_available":has_mapping,"episode_mapping_available":has_episode,"integrity_passed":not any(x.startswith("row_count_mismatch") or x.startswith("non_finite") for x in reasons),"core_evaluable":mode!="incompatible","stateful_evaluable":mode.startswith("stateful") or mode=="full_stateful","episode_evaluable":mode=="full_stateful"}

def audit(resolved: dict, schema_path: Path) -> dict:
    order=read_yaml(schema_path)["ordered_features"]
    return {"required_feature_count":len(order),"benchmarks":[audit_benchmark(x,order) for x in resolved["benchmarks"]]}

