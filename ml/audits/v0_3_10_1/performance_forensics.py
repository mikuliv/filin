"""Воспроизводимый source/log forensics v0.3.10 без запуска обучения."""
from __future__ import annotations
from pathlib import Path


def audit(root: Path) -> dict:
    training = "\n".join((root / "ml/experiments/v0_3_10" / name).read_text(encoding="utf-8")
                         for name in ("run_v0_3_10_stage.py", "build_grouped_oof_predictions.py", "pipeline.py"))
    selection = (root / "ml/experiments/v0_3_10/run_nested_decision_selection.py").read_text(encoding="utf-8")
    sources = training + "\n" + selection
    return {
        "method": "source inspection plus preserved operator timing; no campaign rerun",
        "hardware_baseline": {"cpu": "AMD Ryzen 5 5600X", "cores": 6, "threads": 12,
                              "ram_gib": 64, "gpu": "NVIDIA RTX 5060 Ti", "computers": 1},
        "observed_stage_wall_time": "approximately 5:05",
        "observed_selection_wall_seconds_lower_bound": 3960,
        "observed_selection_note": "selection exceeded 66 minutes",
        "observed_process_cpu_seconds": 14745,
        "estimated_average_busy_threads": 14745 / 3960,
        "estimated_total_cpu_utilization_percent": 100 * 14745 / 3960 / 12,
        "observed_peak_rss_mib_approximate": 782,
        "sequential_candidate_loop": "for parameters in" in selection,
        "nested_outer_fold_loop": "outer" in training and "for" in training,
        "parallel_executor_in_original_sources": any(x in sources for x in ("ProcessPoolExecutor", "multiprocessing.Pool", "Parallel(")),
        "fit_call_occurrences_source_lexical": sources.count(".fit("),
        "bottleneck": "101 independent state-machine policy evaluations were executed serially",
        "gpu_applicability": {"current_pipeline": False,
            "reason": "Frozen scikit-learn HistGradientBoosting, NumPy and Python state-machine path has no CUDA execution path; changing estimator would be a new scientific stage."},
        "claims_are_approximate_where_not_machine_logged": True,
    }
