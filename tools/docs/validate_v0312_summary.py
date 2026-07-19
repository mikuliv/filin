"""Строгая проверка полноты runtime summary v0.3.12."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

SECTIONS=("Назначение этапа","Frozen candidate","Неизменность v0.3.11","Regression protocol freeze","Data access policy","Historical read-only guard","No-fit audit","Benchmark registry","Evaluation coverage","Feature compatibility","Class mapping","Causal mapping","Episode applicability","Input locks","Performance profile","Immutable predictions","Combined prediction hash","v0.3.6 prospective holdout","v0.3.7 hierarchical validation","v0.3.8 evidence validation","v0.3.9 episode-first validation","v0.3.10 minimal-promotion validation","Window-level metrics","Stateful metrics","Episode metrics","Calibration regression","Conformal regression","Legacy pending control","Per-class metrics","Per-run metrics","Cross-benchmark aggregate","Historical references","Comparability audit","Paired comparison","Non-inferiority","Catastrophic regression audit","Drift","Failure analysis","Bootstrap intervals","Prediction performance","CPU utilization","RAM utilization","GPU applicability","Checkpoint and resume","Regression policy result","Readiness for v0.3.13","Ограничения","Следующий этап","Вывод")
TOKENS=("bf40e4bbe820274800d232c22ca299da8cf4dba0003f3a1154d171b658d108be","v0311:19176acb401be2d4","59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7","ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c","62671899371d20a868802b1063001368b50302745592025c8b41defe0f9051de","legacy_pending_affects_v0312_pass_fail","gpu_acceleration_used","candidate_ready_for_v0_3_13_blind_holdout")

def validate(summary: Path):
    errors=[]; text=summary.read_text(encoding="utf-8") if summary.exists() else ""
    for section in SECTIONS:
        if f"## {section}" not in text: errors.append(f"missing section: {section}")
    for token in TOKENS:
        if token not in text: errors.append(f"missing fact: {token}")
    if len(re.findall(r"[0-9a-f]{64}",text))<10: errors.append("insufficient SHA-256 evidence")
    if '"fit_call_count": 0' not in text or '"feature_extraction_call_count": 0' not in text: errors.append("no-fit counters absent")
    if '"v0312_regression_completed": true' not in text or '"v0312_regression_passed": false' not in text: errors.append("readiness flags absent")
    return errors

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--summary",type=Path,required=True); parser.add_argument("--strict",action="store_true"); args=parser.parse_args(); errors=validate(args.summary)
    if errors:
        print("Ошибки summary v0.3.12:"); [print("- "+x) for x in errors]; return 1 if args.strict else 0
    print(f"Summary v0.3.12 validated: {len(SECTIONS)} sections."); return 0
if __name__=="__main__": raise SystemExit(main())

