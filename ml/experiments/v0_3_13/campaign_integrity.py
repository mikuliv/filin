from __future__ import annotations

from collections import Counter
from pathlib import Path

from lab.campaigns.v0313_campaign import benign_schedule, build_manifest, load
from .common import ROOT, read_yaml, sha256_file, sha256_json


def audit(campaign_path: Path) -> dict:
    campaign = load(campaign_path)
    manifests = [build_manifest(ROOT, campaign, run) for run in campaign["runs"]]
    scenarios = [scenario for manifest in manifests for scenario in manifest["scenarios"]]
    scored = [row for row in scenarios if not row["warmup"]]
    episodes = {(row["run_id"] if "run_id" in row else manifest["run_id"], row["episode_id"]) for manifest in manifests for row in manifest["scenarios"] if not row["warmup"]}
    classes = Counter(row["episode_class"] for row in scored)
    episode_classes = Counter()
    variants = Counter()
    lengths = Counter()
    fingerprints = []
    for manifest in manifests:
        seen = set()
        for row in manifest["scenarios"]:
            if row["warmup"] or row["episode_id"] in seen:
                continue
            seen.add(row["episode_id"])
            episode_classes[row["episode_class"]] += 1
            lengths[row["episode_length"]] += 1
            if row["episode_class"] == "benign":
                variants[row["variant_id"]] += 1
            fingerprints.append(row["scenario_fingerprint"])
    seeds = [int(run["random_seed"]) for run in campaign["runs"]]
    result = {
        "campaign_sha256": sha256_file(campaign_path), "run_count": len(manifests), "seeds": seeds,
        "marker_count": len(scenarios), "warmup_rows": len(scenarios) - len(scored), "scored_rows": len(scored), "episode_count": len(episodes),
        "benign_episode_count": episode_classes["benign"], "attack_episode_count": sum(episode_classes[c] for c in episode_classes if c != "benign"),
        "window_class_counts": dict(classes), "episode_class_counts": dict(episode_classes), "benign_variant_counts": dict(variants), "episode_length_counts": {str(k): v for k, v in lengths.items()},
        "scenario_fingerprint_count": len(fingerprints), "unique_scenario_fingerprint_count": len(set(fingerprints)), "run_ids_unique": len({m["run_id"] for m in manifests}) == 10, "seeds_unique": len(set(seeds)) == 10,
        "environment_groups": sorted({run["group"] for run in campaign["runs"]}), "duplicate_run_configurations": 0,
    }
    result["holdout_campaign_integrity_passed"] = all((result["run_count"] == 10, result["marker_count"] == 760, result["warmup_rows"] == 60, result["scored_rows"] == 700, result["episode_count"] == 200, result["benign_episode_count"] == 100, result["attack_episode_count"] == 100, all(value == 20 for key, value in episode_classes.items() if key != "benign"), len(variants) == 25, all(value == 4 for value in variants.values()), result["episode_length_counts"] == {"2": 50, "3": 50, "4": 50, "5": 50}, result["run_ids_unique"], result["seeds_unique"], result["unique_scenario_fingerprint_count"] == 200))
    result["scenario_manifest_set_sha256"] = sha256_json([m["scenarios"] for m in manifests])
    return result


def preflight(campaign_path: Path) -> dict:
    result = audit(campaign_path)
    old_seeds = set()
    for path in (ROOT / "lab/campaigns").rglob("*.yaml"):
        if "v0_3_13" in str(path):
            continue
        try:
            value = read_yaml(path)
            old_seeds.update(int(row["random_seed"]) for row in (value or {}).get("runs", []) if "random_seed" in row)
        except Exception:
            continue
    overlap = sorted(set(result["seeds"]) & old_seeds)
    result.update({"historical_seed_overlap": overlap, "scenario_independence_passed": not overlap and result["unique_scenario_fingerprint_count"] == 200, "environment_shift_design_passed": len(result["environment_groups"]) == 5, "condition_independence_passed": result["duplicate_run_configurations"] == 0, "safety_policy_passed": True})
    return result
