from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import ROOT

REPORT = ROOT / "ml" / "reports" / "v0_4_7_3"
VALIDATION_TOKEN = "validation-v0473-b2a10ef3040e926a"
V0473_VIEWS = (
    "catalog", "summary", "roles", "protocol", "control-pack", "novelty", "isolation", "label-commitment",
    "blindness", "criterion-lineage", "prediction-plan", "active-candidate", "proposal", "inference-progress",
    "recovery", "prediction-packages", "prediction-commitments", "label-unlock", "evaluation", "aggregate-metrics",
    "class-metrics", "confusion-matrices", "episodes", "detection-delay", "abstentions", "previous-failures",
    "comparability", "comparison", "reconstruction", "cards", "gaps", "hypotheses", "mandatory-criteria",
    "manual-review", "decision", "limitations", "export",
)
VIEW_LABELS = dict(zip(V0473_VIEWS, (
    "Каталог проверок", "Сводка", "Роли", "Протокол", "Контрольный набор", "Новизна сценариев",
    "Отсутствие пересечений", "Предварительная фиксация разметки", "Проверка слепого режима",
    "Карта происхождения критериев", "План применения моделей", "Действующий кандидат", "Новое предложение",
    "Ход применения моделей", "Восстановление после прерывания", "Пакеты прогнозов",
    "Предварительные фиксации прогнозов", "Раскрытие разметки", "Оценка", "Общие показатели",
    "Показатели классов", "Матрицы ошибок", "Эпизоды", "Задержка выявления", "Отказы от решения",
    "Шесть прежних проблем", "Сопоставимость", "Сравнение", "Реконструкция", "Карточки", "Разрывы",
    "Гипотезы", "Обязательные критерии", "Ручное рассмотрение", "Итоговое решение", "Ограничения",
    "Выгрузка доказательств",
)))


class CreateValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol_revision: Literal["v0_4_7_3_protocol_r1"]
    role: Literal["control_data_custodian"]


class ValidationOperationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["control_data_custodian", "inference_operator", "evaluation_operator", "validation_reviewer"]
    capability_token: str = Field(pattern=r"^cap-v0473-[a-f0-9]{32}$")
    expected_revision: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=500, pattern=r"^[^<>]*$")


def _load(name: str, default: Any = None) -> Any:
    path = REPORT / name
    if path.suffix == ".json" and path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    if path.is_file():
        return {"document": path.read_text(encoding="utf-8")}
    return {} if default is None else default


def _metric_slice(key: str) -> Any:
    participants = _load("evaluation_bundle.json").get("participants", {})
    field = {"class-metrics": "class_metrics", "confusion-matrices": "confusion_matrix",
             "episodes": "episode_metrics", "detection-delay": "detection_delay", "abstentions": "abstention"}.get(key)
    if field:
        return {name: row.get("metrics", {}).get(field, [] if field in {"class_metrics", "confusion_matrix"} else {}) for name, row in participants.items()}
    return {name: row.get("metrics", {}) for name, row in participants.items()}


def validation_view(view: str = "summary") -> dict[str, Any]:
    if view not in V0473_VIEWS:
        raise KeyError("unknown_v0473_validation_view")
    comparison = _load("comparison_bundle.json")
    mapping: dict[str, Any] = {
        "catalog": {"validations": [VALIDATION_TOKEN], "count": 1}, "summary": _load("v0_4_7_3_policy_result.json"),
        "roles": _load("role_assignments.json"), "protocol": {"path": "incident_reconstruction/protocols/v0_4_7_3_protocol_r1.yaml", "frozen": True},
        "control-pack": _load("control_pack_metadata.json"), "novelty": _load("scenario_novelty_assessment.json"),
        "isolation": _load("data_isolation_report.json"), "label-commitment": _load("label_commitment_metadata.json"),
        "blindness": _load("blindness_report.json"), "criterion-lineage": _load("criterion_lineage_map.json"),
        "prediction-plan": _load("prediction_plan.json"), "active-candidate": _load("active_inference_record.json"),
        "proposal": _load("proposal_inference_record.json"), "inference-progress": {"active": _load("active_inference_record.json"), "proposal": _load("proposal_inference_record.json")},
        "recovery": _load("inference_recovery_record.json"), "prediction-packages": comparison.get("prediction_packages", {}),
        "prediction-commitments": _load("prediction_commitments.json"), "label-unlock": _load("label_unlock_record.json"),
        "evaluation": _load("evaluation_bundle.json"), "aggregate-metrics": _metric_slice("aggregate-metrics"),
        "class-metrics": _metric_slice("class-metrics"), "confusion-matrices": _metric_slice("confusion-matrices"),
        "episodes": _metric_slice("episodes"), "detection-delay": _metric_slice("detection-delay"), "abstentions": _metric_slice("abstentions"),
        "previous-failures": _load("previous_failure_resolution_assessment.json"), "comparability": _load("comparability_assessment.json"),
        "comparison": comparison, "reconstruction": comparison.get("reconstruction", {}), "cards": comparison.get("cards", {}),
        "gaps": comparison.get("gaps", {}), "hypotheses": comparison.get("hypotheses", {}),
        "mandatory-criteria": _load("blind_acceptance_gate.json"), "manual-review": _load("manual_review.json"),
        "decision": _load("final_decision.json"), "limitations": _load("known_limitations.md"), "export": _load("v0_4_7_3_bundle_manifest.json"),
    }
    return {"stage": "v0.4.7.3", "validation_token": VALIDATION_TOKEN, "view": view, "view_label": VIEW_LABELS[view],
            "views": [{"key": key, "label": VIEW_LABELS[key]} for key in V0473_VIEWS], "data": mapping[view],
            "status": "Проверка не пройдена", "technical_status": "failed_validation", "read_only_evidence": True,
            "candidate_registration_allowed": False, "activation_allowed": False, "automatic_promotion_allowed": False,
            "threshold_change_allowed": False, "retraining_allowed": False, "post_unlock_inference_allowed": False,
            "v0_4_8_allowed": False, "next_allowed_stage": "v0.4.7.4"}


class V0473ValidationService:
    TRANSITIONS = ("validate", "commit-control-pack", "check-isolation", "check-blindness", "freeze-plan", "run-active",
                   "run-proposal", "recover-run", "freeze-predictions", "authorize-label-unlock", "unlock-labels", "evaluate", "compare", "reviews", "export")

    def __init__(self, runtime: Path, database: Any):
        self.path, self.database = runtime / "v0473-api-state.json", database

    def list(self) -> list[dict[str, Any]]: return [validation_view("summary")]

    def create(self, request: CreateValidationRequest) -> dict[str, Any]:
        token = "validation-v0473-" + secrets.token_hex(12)
        value = {"validation_token": token, "status": "created", "revision": 0, "next_operation": self.TRANSITIONS[0],
                 "capability_token": "cap-v0473-" + secrets.token_hex(16), "protocol_revision": request.protocol_revision, "labels_unlocked": False}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        self.database.audit("v0473_validation_created", token, request.role)
        return value

    def operate(self, token: str, operation: str, request: ValidationOperationRequest) -> dict[str, Any]:
        if not self.path.is_file(): raise KeyError("validation_not_found")
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if token != value["validation_token"] or request.capability_token != value["capability_token"]: raise KeyError("validation_not_found")
        if request.expected_revision != value["revision"]: raise ValueError("revision_conflict")
        if operation != value["next_operation"]: raise ValueError("invalid_state_transition")
        index = self.TRANSITIONS.index(operation)
        value.update({"status": operation + "_completed", "revision": value["revision"] + 1,
                      "next_operation": self.TRANSITIONS[index + 1] if index + 1 < len(self.TRANSITIONS) else None})
        if operation == "unlock-labels": value["labels_unlocked"] = True
        self.path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        self.database.audit("v0473_" + operation.replace("-", "_"), token, request.role)
        return value
