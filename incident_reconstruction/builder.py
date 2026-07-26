"""Прозрачный детерминированный построитель карточки и комплекта."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .canonical import canonical_bytes, sha256_hex, stable_id
from .validation import CANDIDATE_ID, EVENT_CONTRACT_SHA256, normalize_events, validate_bundle, validate_card


CANDIDATE_ARTIFACT_SHA256 = "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87"
FEATURE_CONTRACT_ID = "network_features_v2"
BUILDER_VERSION = "v0.4.0-r1"
CLASS_TEXT = {
    "auth_failures": ("Наблюдения, совместимые с ошибками аутентификации", "Для установления причины нужны журналы аутентификации."),
    "beacon": ("Наблюдения, совместимые с маячковой активностью", "Для установления назначения соединений нужен анализ узла и назначения."),
    "low_rate_dos": ("Наблюдения, совместимые с низкоинтенсивной нагрузкой", "Для подтверждения отказа нужны показатели доступности сервиса."),
    "port_scan": ("Наблюдения, совместимые со сканированием портов", "Для установления цели активности нужен дополнительный анализ."),
    "web_probe": ("Наблюдения, совместимые с разведочными веб-запросами", "Для установления намерения нужны серверные журналы и контекст запросов."),
}
MITRE = {
    "auth_failures": ("T1110", "Brute Force"), "beacon": ("T1071", "Application Layer Protocol"),
    "low_rate_dos": ("T1498", "Network Denial of Service"), "port_scan": ("T1046", "Network Service Discovery"),
    "web_probe": ("T1595", "Active Scanning"),
}


def _with_id(prefix: str, value: dict[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result[field] = stable_id(prefix, value)
    return result


def _evidence(event: dict[str, Any], incomplete: bool) -> dict[str, Any]:
    value = {
        "schema_version": "evidence_reference_v1", "source_type": "passive_event", "source_id": event["event_id"],
        "source_schema_version": event["schema_version"], "source_sha256": sha256_hex(event),
        "observed_interval": {"start": event["event_timestamp"], "end": None},
        "locator_token": f"events/{event['event_id']}.json", "scope_description": "Поля неизменённого пассивного события.",
        "limitations": (["Дополнительный первичный материал намеренно отсутствует."] if incomplete else ["Источник подтверждает только содержащиеся в событии поля."]),
    }
    return _with_id("evr", value, "evidence_id")


def _facts(event: dict[str, Any], evidence_id: str) -> list[dict[str, Any]]:
    common = {"schema_version": "observed_fact_v1", "subject": event["activity_key"], "start_time": event["event_timestamp"], "end_time": None, "evidence_ids": [evidence_id], "derivation_method": "direct_field_copy", "limitations": ["Факт ограничен полями пассивного события."], "confirmation_status": "source_confirmed"}
    values = [{**common, "fact_type": "network_observation", "predicate": "passive_event_recorded", "value": event["event_type"]}]
    payload = event["payload"]
    if payload.get("alert_class"):
        values.append({**common, "fact_type": "model_output", "predicate": "model_classified_as", "value": payload["alert_class"], "limitations": ["Класс модели не подтверждает намерение или компрометацию."]})
    if payload.get("state") is not None:
        values.append({**common, "fact_type": "episode_rule_output", "predicate": "episode_state_reported", "value": payload["state"]})
    if payload.get("component_status") is not None:
        values.append({**common, "fact_type": "source_integrity", "predicate": "component_status_reported", "value": payload["component_status"]})
    return [_with_id("fact", value, "fact_id") for value in values]


def _hypotheses(facts: list[dict[str, Any]], incomplete: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    model_facts = [fact for fact in facts if fact["predicate"] == "model_classified_as"]
    support = [fact["fact_id"] for fact in (model_facts or facts[:1])]
    alt_base = {"schema_version": "incident_hypothesis_v1", "title": "Альтернативное неинцидентное объяснение", "description": "Наблюдаемая последовательность может иметь разрешённую административную или эксплуатационную причину.", "status": "possible", "supporting_fact_ids": support, "contradicting_fact_ids": [], "missing_evidence": ["Контекст владельца узла и назначение активности."], "alternative_hypothesis_ids": [], "confirmation_conditions": ["Получить независимый контекст активности."], "refutation_conditions": ["Подтвердить отсутствие разрешённой причины."], "support_basis": "transparent_rule_single_event", "limitations": ["Альтернатива не является установленным фактом."]}
    alternative = _with_id("hyp", alt_base, "hypothesis_id")
    if not model_facts:
        title = "Недостаточно данных для гипотезы об инциденте"; description = "Доступные пассивные события не содержат incident-specific результата модели."; status = "insufficient_data"
    else:
        alert_class = str(model_facts[0]["value"]); title, missing = CLASS_TEXT[alert_class]
        description = f"Модель отнесла наблюдаемое поведение к предусмотренному классу {alert_class}. Это аналитическая гипотеза, а не подтверждение действий злоумышленника."
        status = "insufficient_data" if incomplete else ("partially_supported" if len(model_facts) == 1 else "supported_within_available_evidence")
    missing_items = ["Независимый контекст узла и первичные журналы."] if not model_facts else [missing]
    if incomplete: missing_items.append("Полный набор подтверждающих материалов.")
    primary_base = {"schema_version": "incident_hypothesis_v1", "title": title, "description": description, "status": status, "supporting_fact_ids": support, "contradicting_fact_ids": [fact["fact_id"] for fact in facts if fact["predicate"] == "component_status_reported" and fact["value"] == "healthy"], "missing_evidence": missing_items, "alternative_hypothesis_ids": [alternative["hypothesis_id"]], "confirmation_conditions": ["Получить независимые первичные наблюдения, подтверждающие гипотезу."], "refutation_conditions": ["Получить подтверждение разрешённой или неинцидентной причины."], "support_basis": "insufficient_evidence_rule" if status == "insufficient_data" else ("transparent_rule_multiple_events" if len(model_facts) > 1 else "transparent_rule_single_event"), "limitations": ["Гипотеза действительна только в пределах доступных синтетических наблюдений."]}
    primary = _with_id("hyp", primary_base, "hypothesis_id")
    return [primary], [alternative]


def build_incident_card(events: Iterable[dict[str, Any]], laboratory_run_id: str, *, incomplete_evidence: bool = False) -> dict[str, Any]:
    normalized = normalize_events(events)
    references = [_evidence(event, incomplete_evidence) for event in normalized]
    facts = [fact for event, reference in zip(normalized, references) for fact in _facts(event, reference["evidence_id"])]
    facts.sort(key=lambda item: item["fact_id"])
    timeline = []
    for event, reference in zip(normalized, references):
        fact_ids = sorted(fact["fact_id"] for fact in facts if reference["evidence_id"] in fact["evidence_ids"])
        value = {"schema_version": "timeline_item_v1", "start_time": event["event_timestamp"], "end_time": None, "fact_ids": fact_ids, "event_ids": [event["event_id"]], "ordering_basis": "timestamp_then_event_id_without_causal_inference", "time_precision": "exact_source_timestamp", "temporal_uncertainties": ["Совпадающие отметки времени не устанавливают причинность."]}
        timeline.append(_with_id("tli", value, "timeline_item_id"))
    timeline.sort(key=lambda item: (item["start_time"], item["event_ids"][0]))
    hypotheses, alternatives = _hypotheses(facts, incomplete_evidence)
    model_facts = [fact for fact in facts if fact["predicate"] == "model_classified_as"]
    mappings = []
    for fact in model_facts:
        technique_id, name = MITRE[str(fact["value"])]
        mappings.append({"schema_version": "mitre_mapping_v1", "technique_id": technique_id, "technique_name": name, "supporting_fact_ids": [fact["fact_id"]], "mapping_basis": "Аналитическое соответствие frozen класса модели; не доказательство действий конкретного лица.", "limitations": ["Требуется ручная проверка специалистом."], "mapping_status": "analytical_correspondence"})
    basis = [fact["fact_id"] for fact in model_facts] or [facts[0]["fact_id"]]
    rec_base = {"schema_version": "analyst_recommendation_v1", "text": "Специалисту предлагается проверить первичные журналы и контекст узла; автоматические действия не выполнять.", "basis_fact_ids": basis, "priority": "medium", "requires_human_approval": True, "execution_status": "not_executed"}
    recommendation = _with_id("rec", rec_base, "recommendation_id")
    card = {"schema_version": "incident_card_v1", "formed_at": normalized[0]["event_timestamp"], "formation_mode": "deterministic_synthetic_laboratory", "laboratory_run_id": laboratory_run_id, "candidate_id": CANDIDATE_ID, "candidate_artifact_sha256": CANDIDATE_ARTIFACT_SHA256, "feature_contract_id": FEATURE_CONTRACT_ID, "event_contract_sha256": EVENT_CONTRACT_SHA256, "source_event_ids": sorted(event["event_id"] for event in normalized), "evidence_references": sorted(references, key=lambda item: item["evidence_id"]), "observed_facts": facts, "timeline": timeline, "hypotheses": hypotheses, "alternative_hypotheses": alternatives, "contradicting_information": sorted({"Источник одновременно сообщает healthy component status." for fact in facts if fact["predicate"] == "component_status_reported" and fact["value"] == "healthy"}), "missing_information": sorted({item for hypothesis in hypotheses for item in hypothesis["missing_evidence"]}), "mitre_mappings": sorted(mappings, key=lambda item: (item["technique_id"], item["supporting_fact_ids"])), "recommendations": [recommendation], "general_limitations": ["Лабораторные синтетические данные не подтверждают реальный инцидент.", "Результат модели является наблюдаемым источником, а не окончательным выводом."], "safety_declarations": {"laboratory_environment": True, "synthetic_data": True, "automatic_actions_performed": False, "host_compromise_automatically_confirmed": False, "human_analysis_required": True}}
    card["card_id"] = stable_id("card", card)
    card["card_sha256"] = sha256_hex(card)
    validate_card(card, normalized)
    return card


def build_bundle(events: Iterable[dict[str, Any]], laboratory_run_id: str, *, incomplete_evidence: bool = False) -> dict[str, Any]:
    normalized = normalize_events(events)
    card = build_incident_card(normalized, laboratory_run_id, incomplete_evidence=incomplete_evidence)
    semantic_hash = sha256_hex(card)
    files = [{"path": "incident_card.json", "sha256": semantic_hash}, {"path": "passive_events.json", "sha256": sha256_hex(normalized)}]
    manifest_seed = {"files": files, "semantic_result_sha256": semantic_hash}
    manifest = {"bundle_id": stable_id("bundle", manifest_seed), **manifest_seed}
    bundle = {"schema_version": "incident_reconstruction_bundle_v1", "manifest": manifest, "passive_events": normalized, "evidence_references": card["evidence_references"], "incident_card": card, "build_journal": {"run_id": laboratory_run_id, "semantic_result_sha256": semantic_hash, "steps": ["passive_events_validated", "facts_built", "timeline_built", "hypotheses_built", "incident_card_validated"]}, "builder_version": BUILDER_VERSION, "checksums": {"incident_card.json": semantic_hash, "passive_events.json": sha256_hex(normalized)}, "verification_result": "passed", "reproducibility": {"canonical_json": "utf8_sorted_keys_compact", "deterministic_rebuild": True, "git_required": False, "network_required": False, "model_required": False, "backend_required": False}}
    validate_bundle(bundle)
    return bundle


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")
