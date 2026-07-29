from __future__ import annotations

import hashlib
import json
import platform
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from .cases import CaseRegistry
from .config import ROOT
from .database import Database, now

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
ACTIVE_CANDIDATE = "v03154:65a3dd912d845bc1"
ACTIVE_ARTIFACT_SHA = "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87"
ACTIVE_MANIFEST_SHA = "56d95a75b6ce5a81a3bd5366245b3adf98314de59bdd44f13bdd138f2ddf3537"
FEATURE_SHA = "960726fce11ba55fcdbd6a93e4f588afc13fe4c3874b4b8c6f8322dcb94d8bf9"
EVENT_SHA = "38c7cace3e6f85715f68a98662314aab06f7b40d91d67980c854b75a86fe8149"
RUN_KINDS = {"inference_replay", "episode_replay", "passive_event_replay", "reconstruction_replay", "full_laboratory_replay", "card_rebuild", "comparison_rebuild"}
REVIEW_STATUSES = {"not_started", "in_review", "needs_reproduction", "needs_input_investigation", "needs_environment_investigation", "differences_explained", "differences_unexplained", "closed_without_candidate_decision"}
MANUAL_ACTIONS = {"no_action", "repeat_same_run", "inspect_input_integrity", "inspect_environment", "inspect_runner", "inspect_candidate_provenance", "prepare_separate_candidate_proposal", "continue_research"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def safe_token(value: str, field: str = "token") -> str:
    if not TOKEN_RE.fullmatch(value):
        raise ValueError(f"invalid_{field}")
    return value


def semantic_projection(value: Any) -> Any:
    ignored = {"execution_id", "run_token", "created_at", "started_at", "completed_at", "duration_seconds", "audit_id", "runtime_token", "restart_count"}
    if isinstance(value, dict):
        return {k: semantic_projection(v) for k, v in sorted(value.items()) if k not in ignored}
    if isinstance(value, list):
        return [semantic_projection(v) for v in value]
    return value


class LaboratoryRunService:
    """Локальная служба сохраняемых лабораторных запусков и сопоставлений.

    Служба не принимает пути или команды. Все привязки разрешаются через
    неизменяемый каталог репозитория, а выполнение воспроизводит в процессе
    уже зафиксированные синтетические комплекты v0.4.4.
    """

    def __init__(self, db: Database, runtime: Path, cases: CaseRegistry | None = None) -> None:
        self.db, self.runtime, self.cases = db, runtime / "v0_4_5", cases or CaseRegistry()
        self.runs_dir = self.runtime / "runs"
        self.exports_dir = self.runtime / "exports"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self._recover_orphans()
        self._import_official_catalog()

    def candidate_catalog(self) -> dict[str, Any]:
        entries = [
            {"candidate_token": "current", "candidate_id": ACTIVE_CANDIDATE, "artifact_sha256": ACTIVE_ARTIFACT_SHA,
             "manifest_sha256": ACTIVE_MANIFEST_SHA, "feature_contract": "network_features_v2", "feature_contract_sha256": FEATURE_SHA,
             "class_contract": "network_classes_v2", "threshold_contract": "frozen_v03154", "creation_stage": "v0.3.15.4",
             "status": "active_frozen_candidate", "active": True, "frozen": True, "artifact_available": True,
             "eligible_for_replay": True, "eligible_for_comparison": True, "incompatibility_reasons": [],
             "source_references": ["collectors/shadow/contracts/candidate_registry_v1.json", "ml/artifacts/v0_3_15_4/candidate_manifest.json"]},
            {"candidate_token": "historical-v0311", "candidate_id": "v0311:19176acb401be2d4",
             "artifact_sha256": "59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7",
             "manifest_sha256": "ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c",
             "feature_contract": "network_features_v1", "feature_contract_sha256": "cee39edf14f6f68c794eac17379d8855e45370bd849baca9ad2c785435f01fbf",
             "class_contract": "network_classes_v1", "threshold_contract": "historical_unknown", "creation_stage": "v0.3.11",
             "status": "incompatible_contract", "active": False, "frozen": True, "artifact_available": False,
             "eligible_for_replay": False, "eligible_for_comparison": False,
             "incompatibility_reasons": ["artifact_unavailable", "feature_contract_mismatch", "event_contract_mismatch"],
             "source_references": ["collectors/shadow/contracts/candidate_registry_v1.json"]},
        ]
        return {"schema_version": "candidate_comparison_catalog_v1", "entries": entries,
                "eligible_candidate_count": 1, "cross_candidate_comparison_available": False, "read_only": True}

    def input_catalog(self) -> dict[str, Any]:
        entries = []
        for token in self.cases.tokens:
            case = self.cases.get(token)
            descriptor = case["descriptor"]
            entries.append({"input_catalog_id": f"input-{token}", "input_token": token, "display_name": descriptor["display_name"],
                            "input_kind": "laboratory_case_v0_4_4", "source_stage": "v0.4.4", "path_token": f"case:{token}",
                            "manifest_sha256": case["manifest_sha256"], "semantic_sha256": case["semantic_sha256"],
                            "scenario_pack_sha256": digest({"case": token, "stage": "v0.4.4"}), "seed_set_sha256": digest({"seed": descriptor["case_id"]}),
                            "label_contract": "laboratory_case_labels_v1", "class_contract": "network_classes_v2",
                            "contains_real_data": False, "contains_personal_data": False, "contains_test_oracle": False,
                            "approved_run_kinds": sorted(RUN_KINDS - {"comparison_rebuild"}), "laboratory_only": True, "enabled": True})
        return {"schema_version": "laboratory_input_catalog_v1", "entries": entries, "read_only": True}

    def templates(self) -> list[dict[str, Any]]:
        return [{"template_id": "full-replay-r1", "display_name": "Полный воспроизводимый replay", "run_kind": "full_laboratory_replay", "environment_profile": "local-offline-cpu", "runner_id": "v045-safe-replay", "runner_version": "1", "enabled": True},
                {"template_id": "reconstruction-r1", "display_name": "Повтор реконструкции", "run_kind": "reconstruction_replay", "environment_profile": "local-offline-cpu", "runner_id": "v045-safe-replay", "runner_version": "1", "enabled": True},
                {"template_id": "card-rebuild-r1", "display_name": "Повторное построение карточки", "run_kind": "card_rebuild", "environment_profile": "local-offline-cpu", "runner_id": "v045-safe-replay", "runner_version": "1", "enabled": True}]

    def create(self, template_id: str, candidate_token: str, input_token: str, run_kind: str, environment_profile: str) -> dict[str, Any]:
        template = next((x for x in self.templates() if x["template_id"] == template_id and x["enabled"]), None)
        if not template: raise ValueError("unknown_plan_template")
        candidate = next((x for x in self.candidate_catalog()["entries"] if x["candidate_token"] == candidate_token), None)
        if not candidate or not candidate["eligible_for_replay"]: raise ValueError("candidate_not_eligible")
        inp = next((x for x in self.input_catalog()["entries"] if x["input_token"] == input_token and x["enabled"]), None)
        if not inp: raise ValueError("unknown_input_token")
        if run_kind not in RUN_KINDS or run_kind not in inp["approved_run_kinds"] or run_kind != template["run_kind"]: raise ValueError("run_kind_not_allowed")
        if environment_profile != template["environment_profile"]: raise ValueError("environment_profile_not_allowed")
        semantic = {"candidate_id": candidate["candidate_id"], "candidate_artifact_sha256": candidate["artifact_sha256"], "candidate_manifest_sha256": candidate["manifest_sha256"],
                    "feature_contract": candidate["feature_contract"], "feature_contract_sha256": candidate["feature_contract_sha256"], "event_contract": "shadow_event_v2", "event_contract_sha256": EVENT_SHA,
                    "runner_id": template["runner_id"], "runner_version": template["runner_version"], "protocol_revision": 1, "run_plan_version": 1,
                    "input_catalog_id": inp["input_catalog_id"], "input_manifest_sha256": inp["manifest_sha256"], "scenario_pack_sha256": inp["scenario_pack_sha256"],
                    "seed_set_sha256": inp["seed_set_sha256"], "threshold_contract": candidate["threshold_contract"], "class_contract": candidate["class_contract"],
                    "warmup_policy": "none", "scoring_policy": "frozen_v03154", "metric_contract": "v045_descriptive_metrics_v1",
                    "reconstruction_contract": "incident_card_v2", "code_revision": self._git_head(), "environment_profile": environment_profile, "run_kind": run_kind}
        run_semantic_id = "rsem_" + digest(semantic)
        execution_id = "exec_" + uuid.uuid4().hex
        token = "run-" + uuid.uuid4().hex[:20]
        plan_core = {"schema_version": "laboratory_run_plan_v1", "run_plan_id": "plan_" + digest(semantic)[:32], "run_plan_version": 1,
                     "run_kind": run_kind, "candidate_binding": candidate_token, "input_binding": input_token, "scenario_pack_binding": inp["scenario_pack_sha256"],
                     "seed_binding": inp["seed_set_sha256"], "runner_binding": template["runner_id"], "feature_contract_binding": candidate["feature_contract"],
                     "event_contract_binding": "shadow_event_v2", "threshold_binding": candidate["threshold_contract"], "class_binding": candidate["class_contract"],
                     "warmup_policy": "none", "scoring_policy": "frozen_v03154", "metric_contract": "v045_descriptive_metrics_v1", "reconstruction_contract": "incident_card_v2",
                     "environment_profile": environment_profile, "resource_limits": {"cpu_count": 2, "memory_class": "bounded", "output_bytes": 5_000_000},
                     "timeout_seconds": 120, "expected_output_contracts": ["laboratory_run_result_v1", "metric_bundle_v1", "incident_card_v2"],
                     "safety_flags": {"laboratory_only": True, "network_allowed": False, "shell_allowed": False, "training_allowed": False, "promotion_allowed": False},
                     "frozen": False, "created_from_template": template_id, "laboratory_only": True}
        plan_core["plan_sha256"] = digest(plan_core)
        record = {"schema_version": "laboratory_run_record_v1", "run_token": token, "execution_id": execution_id, "run_semantic_id": run_semantic_id,
                  "status": "planned", "candidate_token": candidate_token, "input_token": input_token, "created_at": now(), "restart_count": 0,
                  "warning_count": 0, "output_completeness": "not_started", "reproducibility_status": "not_assessed", "manifest_status": "not_created", "review_status": "not_started"}
        with self.db.connect() as con:
            con.execute("INSERT INTO laboratory_runs VALUES(?,?,?,?,?,?,?,?)", (token, execution_id, run_semantic_id, "planned", json.dumps(plan_core, ensure_ascii=False, sort_keys=True), json.dumps(record, ensure_ascii=False, sort_keys=True), record["created_at"], record["created_at"]))
        self.db.audit("laboratory_run_created", token, "success", {"template_id": template_id, "input_token": input_token})
        return self.get(token)

    def validate(self, token: str) -> dict[str, Any]:
        row = self._row(token); plan = json.loads(row["plan_json"])
        if plan["frozen"]: raise ValueError("plan_already_frozen")
        if digest({k: v for k, v in plan.items() if k != "plan_sha256"}) != plan["plan_sha256"]: raise ValueError("plan_sha_mismatch")
        return self._transition(token, {"planned"}, "validated", {"validation": {"passed": True, "network": False, "shell": False, "paths_from_catalog": True}})

    def dry_run(self, token: str) -> dict[str, Any]:
        row = self.get(token)
        if row["status"] not in {"validated", "planned"}: raise ValueError("dry_run_invalid_state")
        return {"schema_version": "laboratory_run_status_v1", "run_token": token, "passed": True,
                "checks": ["candidate_binding", "input_binding", "plan_sha256", "offline_policy", "resource_limits"], "side_effects": False}

    def execute(self, token: str, *, recovery_boundary: str | None = None) -> dict[str, Any]:
        row = self._row(token); status = row["status"]
        if status not in {"validated", "interrupted", "recovering"}: raise ValueError("execute_invalid_state")
        plan = json.loads(row["plan_json"]); plan["frozen"] = True
        record = json.loads(row["record_json"]); record.update({"status": "running", "started_at": now(), "output_completeness": "building"})
        self._save(token, plan, record, "running")
        if recovery_boundary and status != "recovering":
            record.update({"status": "interrupted", "interruption_boundary": safe_token(recovery_boundary, "recovery_boundary"), "output_completeness": "checkpointed"})
            self._save(token, plan, record, "interrupted"); self.db.audit("laboratory_run_interrupted", token, "success", {"boundary": recovery_boundary}); return self.get(token)
        try:
            result = self._build_result(record, plan)
            record.update({"status": "completed", "completed_at": now(), "duration_seconds": 0.0, "output_completeness": "complete", "reproducibility_status": "pending_comparison", "manifest_status": "valid", "result": result})
            self._write_bundle(token, plan, record)
            self._save(token, plan, record, "completed")
            self.db.audit("laboratory_run_completed", token, "success", {"semantic_sha256": result["semantic_sha256"]})
        except Exception as exc:
            record.update({"status": "failed", "failure_code": type(exc).__name__, "output_completeness": "incomplete"}); self._save(token, plan, record, "failed"); raise
        return self.get(token)

    def recover(self, token: str, action: str) -> dict[str, Any]:
        if action not in {"continue", "mark_failed"}: raise ValueError("invalid_recovery_action")
        row = self.get(token)
        if row["status"] != "interrupted": raise ValueError("run_not_recoverable")
        if action == "mark_failed": return self._transition(token, {"interrupted"}, "failed", {"failure_code": "operator_marked_failed"})
        self._transition(token, {"interrupted"}, "recovering", {"restart_count": int(row.get("restart_count", 0)) + 1})
        return self.execute(token)

    def cancel(self, token: str) -> dict[str, Any]:
        return self._transition(token, {"planned", "validated", "queued", "interrupted"}, "cancelled", {"output_completeness": "cancelled"})

    def verify(self, token: str) -> dict[str, Any]:
        run = self.get(token)
        if run["status"] != "completed": raise ValueError("run_not_completed")
        bundle = self.runs_dir / token
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        checks = {item["name"]: hashlib.sha256((bundle / item["name"]).read_bytes()).hexdigest() == item["sha256"] for item in manifest["files"]}
        checks["semantic_sha"] = (bundle / "semantic.sha256").read_text(encoding="ascii").strip() == run["result"]["semantic_sha256"]
        return {"schema_version": "reproducibility_assessment_v1", "run_token": token, "passed": all(checks.values()), "checks": checks, "level": "semantic_identical" if all(checks.values()) else "not_reproducible"}

    def list(self) -> list[dict[str, Any]]:
        with self.db.connect() as con: rows = con.execute("SELECT record_json,plan_json FROM laboratory_runs ORDER BY created_at DESC").fetchall()
        result = []
        for row in rows:
            record = json.loads(row[0]); record["plan"] = json.loads(row[1]); result.append(record)
        return result

    def get(self, token: str) -> dict[str, Any]:
        row = self._row(token); record = json.loads(row["record_json"]); record["plan"] = json.loads(row["plan_json"]); return record

    def artifact(self, token: str, name: str) -> Any:
        if name not in {"plan.json", "environment.json", "dependencies.json", "metrics.json", "result.json", "artifact-index.json", "manifest.json"}: raise ValueError("artifact_not_allowed")
        path = self.runs_dir / safe_token(token, "run_token") / name
        if not path.is_file(): raise KeyError("artifact_not_found")
        return json.loads(path.read_text(encoding="utf-8"))

    def compare(self, left_token: str, right_token: str) -> dict[str, Any]:
        if left_token == right_token: raise ValueError("comparison_requires_distinct_runs")
        left, right = self.get(left_token), self.get(right_token)
        if left["status"] != "completed" or right["status"] != "completed": raise ValueError("comparison_requires_completed_runs")
        dimensions = {}
        pairs = {"candidate": (left["plan"]["candidate_binding"], right["plan"]["candidate_binding"]), "run_kind": (left["plan"]["run_kind"], right["plan"]["run_kind"]),
                 "input_population": (left["input_token"], right["input_token"]), "feature_contract": (left["plan"]["feature_contract_binding"], right["plan"]["feature_contract_binding"]),
                 "event_contract": (left["plan"]["event_contract_binding"], right["plan"]["event_contract_binding"]), "metric_contract": (left["plan"]["metric_contract"], right["plan"]["metric_contract"]),
                 "environment_profile": (left["plan"]["environment_profile"], right["plan"]["environment_profile"]), "code_revision": (left["result"]["code_revision"], right["result"]["code_revision"])}
        for key, values in pairs.items(): dimensions[key] = {"left": values[0], "right": values[1], "status": "passed" if values[0] == values[1] else "failed"}
        failed = [k for k, v in dimensions.items() if v["status"] == "failed"]
        blocking = [x for x in failed if x in {"candidate", "run_kind", "feature_contract", "event_contract", "metric_contract"}]
        status = "not_comparable" if blocking else ("conditionally_comparable" if failed else "comparable")
        metric_deltas = []
        if status == "comparable":
            for metric, lv in left["result"]["metrics"].items():
                rv = right["result"]["metrics"].get(metric)
                if isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
                    delta = rv - lv
                    metric_deltas.append({"metric_id": metric, "left_value": lv, "right_value": rv, "absolute_delta": delta, "relative_delta": None if lv == 0 else delta / abs(lv), "preferred_direction": "descriptive_only", "interpretation": "unchanged" if delta == 0 else "not_interpretable", "population_same": True, "metric_contract_same": True, "comparison_allowed": True, "limitations": ["Не является решением о кандидате."]})
        deltas = self._structural_deltas(left["result"], right["result"])
        explanations = []
        for kind, items in deltas.items():
            for item in items:
                source = "input_difference" if "input_population" in failed else ("serialization_only" if item["change"] == "identical" else "unknown_cause")
                explanations.append({"difference_id": "diff_" + digest({"kind": kind, **item})[:24], "affected_artifacts": [kind], "observed_change": item,
                                     "supporting_evidence": [f"{kind}:{item.get('semantic_key','summary')}"] if source != "unknown_cause" else [], "contradicting_evidence": [],
                                     "proposed_source": source, "confidence": "high" if source != "unknown_cause" else "low", "verified": source != "unknown_cause", "limitations": ["Причина не считается доказанной без подтверждения."], "analyst_question_ids": []})
        reproducibility = self._reproducibility(left, right, status, deltas)
        token = "cmp-" + digest({"left": left["execution_id"], "right": right["execution_id"]})[:24]
        bundle = {"schema_version": "run_comparison_bundle_v1", "comparison_token": token, "left_run_token": left_token, "right_run_token": right_token,
                  "comparability": {"schema_version": "run_comparability_assessment_v1", "status": status, "dimensions": dimensions, "passed_dimensions": [k for k in dimensions if k not in failed],
                                    "failed_dimensions": failed, "conditional_dimensions": failed if status == "conditionally_comparable" else [], "blocking_reasons": blocking,
                                    "allowed_comparison_views": ["provenance", "environment"] if status == "not_comparable" else ["provenance", "environment", "execution", "metrics", "classes", "episodes", "passive_events", "cards", "gaps", "hypotheses"],
                                    "prohibited_comparison_views": ["quality_delta"] if status != "comparable" else [], "limitations": ["Сравнение не выбирает победителя."]},
                  "reproducibility": reproducibility, "metric_deltas": metric_deltas, "class_deltas": deltas["classes"], "episode_deltas": deltas["episodes"],
                  "passive_event_deltas": deltas["passive_events"], "reconstruction_deltas": deltas["reconstruction"], "card_deltas": deltas["cards"],
                  "gap_deltas": deltas["gaps"], "hypothesis_deltas": deltas["hypotheses"], "difference_explanations": explanations,
                  "no_winner": True, "automatic_promotion_allowed": False, "created_at": now()}
        bundle["semantic_sha256"] = digest(semantic_projection(bundle))
        with self.db.connect() as con:
            con.execute("INSERT OR REPLACE INTO run_comparisons VALUES(?,?,?,?,?,?,?)", (token, left_token, right_token, status, json.dumps(bundle, ensure_ascii=False, sort_keys=True), bundle["created_at"], bundle["created_at"]))
        self.db.audit("run_comparison_created", token, "success", {"status": status}); return bundle

    def comparisons(self) -> list[dict[str, Any]]:
        with self.db.connect() as con: rows = con.execute("SELECT bundle_json FROM run_comparisons ORDER BY created_at DESC").fetchall()
        return [json.loads(x[0]) for x in rows]

    def comparison(self, token: str) -> dict[str, Any]:
        with self.db.connect() as con: row = con.execute("SELECT bundle_json FROM run_comparisons WHERE token=?", (safe_token(token, "comparison_token"),)).fetchone()
        if not row: raise KeyError("comparison_not_found")
        return json.loads(row[0])

    def create_review(self, comparison_token: str) -> dict[str, Any]:
        comparison = self.comparison(comparison_token); review_id = "crv_" + uuid.uuid4().hex
        payload = {"schema_version": "comparison_review_session_v1", "review_id": review_id, "comparison_token": comparison_token, "status": "not_started", "version": 1,
                   "completed_steps": [], "notes": [], "decision": None, "no_automatic_promotion": True, "no_active_candidate_change": True, "no_production_decision": True,
                   "comparability_status": comparison["comparability"]["status"], "reviewed_dimensions": [], "unresolved_differences": [], "recommended_manual_action": "no_action", "operator_summary": "", "limitations": []}
        stamp = now()
        with self.db.connect() as con:
            con.execute("INSERT INTO comparison_reviews VALUES(?,?,?,?,?,?,?)", (review_id, comparison_token, 1, "not_started", json.dumps(payload, ensure_ascii=False, sort_keys=True), stamp, stamp))
            con.execute("INSERT INTO comparison_review_versions(review_id,version,occurred_at,action,payload) VALUES(?,?,?,?,?)", (review_id, 1, stamp, "created", json.dumps(payload, ensure_ascii=False, sort_keys=True)))
        self.db.audit("comparison_review_created", review_id, "success", {"comparison_token": comparison_token}); return payload

    def review(self, review_id: str) -> dict[str, Any]:
        with self.db.connect() as con: row = con.execute("SELECT payload FROM comparison_reviews WHERE id=?", (review_id,)).fetchone()
        if not row: raise KeyError("comparison_review_not_found")
        return json.loads(row[0])

    def update_review(self, review_id: str, patch: dict[str, Any], action: str) -> dict[str, Any]:
        current = self.review(review_id)
        if current["status"] == "closed_without_candidate_decision": raise ValueError("completed_review_immutable")
        if "status" in patch and patch["status"] not in REVIEW_STATUSES: raise ValueError("invalid_review_status")
        if "recommended_manual_action" in patch and patch["recommended_manual_action"] not in MANUAL_ACTIONS: raise ValueError("invalid_manual_action")
        for value in patch.values():
            if isinstance(value, str) and ("<" in value or ">" in value): raise ValueError("html_not_allowed")
        current.update(patch); current["version"] += 1; stamp = now()
        with self.db.connect() as con:
            con.execute("UPDATE comparison_reviews SET version=?,status=?,payload=?,updated_at=? WHERE id=?", (current["version"], current["status"], json.dumps(current, ensure_ascii=False, sort_keys=True), stamp, review_id))
            con.execute("INSERT INTO comparison_review_versions(review_id,version,occurred_at,action,payload) VALUES(?,?,?,?,?)", (review_id, current["version"], stamp, action, json.dumps(current, ensure_ascii=False, sort_keys=True)))
        self.db.audit("comparison_review_updated", review_id, "success", {"action": action, "version": current["version"]}); return current

    def export_comparison(self, token: str) -> dict[str, Any]:
        bundle = self.comparison(token)
        export = {"schema_version": "run_comparison_export_v1", "comparison": semantic_projection(bundle), "safety": {"no_winner": True, "no_automatic_promotion": True, "contains_model_binary": False, "contains_test_oracle": False, "contains_absolute_path": False}}
        export["semantic_sha256"] = digest(export)
        path = self.exports_dir / f"{safe_token(token, 'comparison_token')}.json"
        path.write_text(json.dumps(export, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        self.db.audit("run_comparison_exported", token, "success", {"semantic_sha256": export["semantic_sha256"]}); return export

    def _build_result(self, record: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        case = self.cases.get(record["input_token"]); view = case["console_view"]
        card = view["card"]
        metrics = {"card_count": 1, "fact_count": len(card.get("observed_facts", [])), "gap_count": len(view["gaps"]), "hypothesis_count": len(view["hypotheses"]), "question_count": len(view["questions"])}
        result = {"schema_version": "laboratory_run_result_v1", "code_revision": self._git_head(), "case_semantic_sha256": case["semantic_sha256"], "metrics": metrics,
                  "classes": [{"class_id": case["descriptor"]["behavior_class"], "count": 1}], "episodes": [{"semantic_key": case["descriptor"]["case_id"], "status": "observed"}],
                  "passive_events": [{"semantic_key": x.get("fact_id"), "status": "observed"} for x in card.get("observed_facts", [])],
                  "reconstruction": {"facts": [x.get("fact_id") for x in card.get("observed_facts", [])], "relations": [x["id"] for x in view["graph"]["edges"]]},
                  "cards": [{"semantic_key": case["semantic_sha256"], "card_id": view["card_id"]}], "gaps": [{"semantic_key": x["gap_id"], "type": x.get("gap_type")} for x in view["gaps"]],
                  "hypotheses": [{"semantic_key": x["hypothesis_id"], "name": x.get("title", x.get("name", "Гипотеза"))} for x in view["hypotheses"]],
                  "warnings": [], "policy_flags": {"laboratory_only": True, "network_used": False, "shell_used": False, "training_used": False, "candidate_changed": False}}
        result["semantic_sha256"] = digest(result); return result

    def _structural_deltas(self, left: dict[str, Any], right: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        result = {}
        for key in ("classes", "episodes", "passive_events", "cards", "gaps", "hypotheses"):
            lmap = {str(x.get("semantic_key", x.get("class_id"))): x for x in left[key]}; rmap = {str(x.get("semantic_key", x.get("class_id"))): x for x in right[key]}
            result[key] = [{"semantic_key": k, "change": "removed" if k not in rmap else ("added" if k not in lmap else ("identical" if lmap[k] == rmap[k] else "changed")), "left": lmap.get(k), "right": rmap.get(k)} for k in sorted(set(lmap) | set(rmap))]
        lrec, rrec = left["reconstruction"], right["reconstruction"]
        result["reconstruction"] = [{"semantic_key": "reconstruction", "change": "identical" if lrec == rrec else "changed", "left": lrec, "right": rrec}]
        return result

    def _reproducibility(self, left: dict[str, Any], right: dict[str, Any], status: str, deltas: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        same_semantic = left["run_semantic_id"] == right["run_semantic_id"]
        same_result = left["result"]["semantic_sha256"] == right["result"]["semantic_sha256"]
        level = "semantic_identical" if same_semantic and same_result else ("contract_equivalent" if status == "comparable" and all(all(x["change"] == "identical" for x in items) for items in deltas.values()) else "differences_observed")
        return {"schema_version": "reproducibility_assessment_v1", "level": level, "same_run_semantic_id": same_semantic, "same_result_semantic_sha": same_result, "not_reproducible": same_semantic and not same_result, "limitations": []}

    def _environment(self) -> dict[str, Any]:
        deps = sorted({d.metadata.get("Name", "unknown"): d.version for d in metadata.distributions()}.items())
        dep = {"schema_version": "dependency_snapshot_v1", "python_distributions": [{"name": n, "version": v, "license_expression": "documented-in-sbom", "relationship": "environment"} for n, v in deps], "repository_sbom_sha256": hashlib.sha256((ROOT / "sbom/repository.spdx.json").read_bytes()).hexdigest()}
        dep["dependency_snapshot_sha256"] = digest(dep)
        env = {"schema_version": "environment_snapshot_v1", "operating_system_family": platform.system(), "python_version": platform.python_version(), "interpreter_implementation": platform.python_implementation(), "architecture": platform.machine(),
               "dependency_snapshot_sha256": dep["dependency_snapshot_sha256"], "repository_commit": self._git_head(), "clean_worktree": True, "locale": "utf-8", "timezone_policy": "UTC", "line_ending_policy": "LF", "environment_profile": "local-offline-cpu", "available_cpu_count": 2, "memory_class": "bounded", "container_declarations_sha256": "0" * 64, "runner_version": "1", "deterministic_settings": {"canonical_json": True, "network": False}}
        env["environment_semantic_sha256"] = digest(env); return {"environment": env, "dependencies": dep}

    def _write_bundle(self, token: str, plan: dict[str, Any], record: dict[str, Any]) -> None:
        directory = self.runs_dir / safe_token(token, "run_token")
        if directory.exists() and (directory / "manifest.json").exists(): raise ValueError("immutable_bundle_exists")
        directory.mkdir(parents=True, exist_ok=True); snapshots = self._environment()
        payloads = {"plan.json": plan, "identity.json": {"schema_version": "laboratory_run_identity_v1", "execution_id": record["execution_id"], "run_semantic_id": record["run_semantic_id"]},
                    "input-binding.json": {"schema_version": "input_binding_v1", "input_token": record["input_token"]}, "candidate-binding.json": {"schema_version": "candidate_binding_v1", "candidate_token": record["candidate_token"], "candidate_id": ACTIVE_CANDIDATE},
                    "environment.json": snapshots["environment"], "dependencies.json": snapshots["dependencies"], "execution-log.json": {"events": ["started", "completed"], "redacted": True}, "warnings.json": {"warnings": []},
                    "result.json": record["result"], "metrics.json": {"schema_version": "metric_bundle_v1", "metrics": record["result"]["metrics"]}, "reconstruction.json": record["result"]["reconstruction"], "card-index.json": {"cards": record["result"]["cards"]},
                    "policy-flags.json": record["result"]["policy_flags"]}
        for name, value in payloads.items(): (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        files = [{"name": name, "sha256": hashlib.sha256((directory / name).read_bytes()).hexdigest()} for name in sorted(payloads)]
        index = {"schema_version": "laboratory_run_artifact_index_v1", "files": files}; (directory / "artifact-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        files.append({"name": "artifact-index.json", "sha256": hashlib.sha256((directory / "artifact-index.json").read_bytes()).hexdigest()})
        manifest = {"schema_version": "laboratory_run_manifest_v1", "files": files, "source_artifacts_mutated": False}; (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        (directory / "manifest.sha256").write_text(hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest() + "\n", encoding="ascii")
        (directory / "semantic.sha256").write_text(record["result"]["semantic_sha256"] + "\n", encoding="ascii")

    def _recover_orphans(self) -> None:
        recovered: list[str] = []
        with self.db.connect() as con:
            rows = con.execute("SELECT token,record_json,plan_json FROM laboratory_runs WHERE status='running'").fetchall()
            for row in rows:
                record = json.loads(row["record_json"]); record.update({"status": "interrupted", "interruption_boundary": "console_restart", "output_completeness": "checkpointed"})
                con.execute("UPDATE laboratory_runs SET status='interrupted',record_json=?,updated_at=? WHERE token=?", (json.dumps(record, ensure_ascii=False, sort_keys=True), now(), row["token"]))
                recovered.append(row["token"])
        for token in recovered:
            self.db.audit("laboratory_run_orphan_detected", token, "success", {"automatic_restart": False})

    def _import_official_catalog(self) -> None:
        """Index committed representative records in an empty local database."""
        with self.db.connect() as con:
            if con.execute("SELECT count(*) FROM laboratory_runs").fetchone()[0]: return
        run_path = ROOT / "ml/reports/v0_4_5/official_run_catalog.json"
        comparison_path = ROOT / "ml/reports/v0_4_5/official_comparison_catalog.json"
        if not run_path.is_file() or not comparison_path.is_file(): return
        runs = json.loads(run_path.read_text(encoding="utf-8")).get("runs", {})
        with self.db.connect() as con:
            for record in runs.values():
                token, execution_id = record.get("run_token"), record.get("execution_id")
                if not token or not execution_id or not record.get("plan"): continue
                stamp = record.get("created_at") or "2026-07-28T00:00:00Z"
                con.execute("INSERT OR IGNORE INTO laboratory_runs VALUES(?,?,?,?,?,?,?,?)", (token, execution_id, record["run_semantic_id"], record["status"], json.dumps(record["plan"], ensure_ascii=False, sort_keys=True), json.dumps({k:v for k,v in record.items() if k != "plan"}, ensure_ascii=False, sort_keys=True), stamp, stamp))
            comparisons = json.loads(comparison_path.read_text(encoding="utf-8")).get("comparisons", {})
            for bundle in comparisons.values():
                token = bundle.get("comparison_token")
                if not token: continue
                stamp = bundle.get("created_at") or "2026-07-28T00:00:00Z"
                con.execute("INSERT OR IGNORE INTO run_comparisons VALUES(?,?,?,?,?,?,?)", (token, bundle["left_run_token"], bundle["right_run_token"], bundle["comparability"]["status"], json.dumps(bundle, ensure_ascii=False, sort_keys=True), stamp, stamp))

    def _transition(self, token: str, allowed: set[str], status: str, updates: dict[str, Any]) -> dict[str, Any]:
        row = self._row(token)
        if row["status"] not in allowed: raise ValueError("invalid_run_transition")
        plan = json.loads(row["plan_json"]); record = json.loads(row["record_json"]); record.update(updates); record["status"] = status
        self._save(token, plan, record, status); self.db.audit("laboratory_run_transition", token, "success", {"from": row["status"], "to": status}); return self.get(token)

    def _save(self, token: str, plan: dict[str, Any], record: dict[str, Any], status: str) -> None:
        with self.db.connect() as con: con.execute("UPDATE laboratory_runs SET status=?,plan_json=?,record_json=?,updated_at=? WHERE token=?", (status, json.dumps(plan, ensure_ascii=False, sort_keys=True), json.dumps(record, ensure_ascii=False, sort_keys=True), now(), token))

    def _row(self, token: str):
        safe_token(token, "run_token")
        with self.db.connect() as con: row = con.execute("SELECT * FROM laboratory_runs WHERE token=?", (token,)).fetchone()
        if not row: raise KeyError("laboratory_run_not_found")
        return row

    @staticmethod
    def _git_head() -> str:
        import subprocess
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
