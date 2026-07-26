from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from incident_reconstruction.builder import build_bundle
from incident_reconstruction.canonical import sha256_hex, stable_id
from incident_reconstruction.hypothesis import build_hypothesis_bundle
from incident_reconstruction.scenarios import make_event
from incident_reconstruction.temporal import build_temporal_bundle, explain_relation
from lab_console.config import ROOT

CANDIDATE_ID = "v03154:65a3dd912d845bc1"
SEED_NAMESPACE = "v044-r1-seed-64000-64199"
CATALOG_PATH = ROOT / "lab_console/cases/laboratory_case_catalog_v1.yaml"
REPORT_CASES = ROOT / "ml/reports/v0_4_4/cases"

CASE_SPECS: tuple[dict[str, Any], ...] = (
    {"token":"normal","case_id":"lab_normal_activity","display_name":"Нормальная сетевая активность","short_description":"Обычный разрешённый обмен без искусственного подозрительного вывода.","behavior_class":"normal","difficulty":"basic","tags":["normal","baseline"],"alert":None,"events":2,"variant":"normal"},
    {"token":"auth","case_id":"lab_auth_failures","display_name":"Серия ошибок аутентификации","short_description":"Повторяющиеся ошибки входа с административными и подозрительными альтернативами.","behavior_class":"auth_failures","difficulty":"intermediate","tags":["authentication","alternatives"],"alert":"auth_failures","events":3,"variant":"series"},
    {"token":"beacon","case_id":"lab_beacon_activity","display_name":"Периодическая маячковая активность","short_description":"Периодические соединения, допускающие служебное и подозрительное объяснение.","behavior_class":"beacon","difficulty":"advanced","tags":["periodic","alternatives"],"alert":"beacon","events":3,"variant":"periodic"},
    {"token":"low-load","case_id":"lab_low_rate_load","display_name":"Низкоинтенсивная нагрузка на сервис","short_description":"Редкие запросы и технические альтернативы без вывода об атаке.","behavior_class":"low_rate_dos","difficulty":"intermediate","tags":["service","low-rate"],"alert":"low_rate_dos","events":3,"variant":"series"},
    {"token":"port-scan","case_id":"lab_port_scan","display_name":"Сканирование портов","short_description":"Наблюдения, совместимые с инвентаризацией или разведкой.","behavior_class":"port_scan","difficulty":"intermediate","tags":["ports","inventory"],"alert":"port_scan","events":2,"variant":"series"},
    {"token":"web-probe","case_id":"lab_web_probe","display_name":"Разведочные веб-запросы","short_description":"Веб-запросы с мониторинговой и разведочной альтернативами.","behavior_class":"web_probe","difficulty":"advanced","tags":["web","monitoring"],"alert":"web_probe","events":3,"variant":"series"},
    {"token":"mixed","case_id":"lab_mixed_multi_episode","display_name":"Смешанный многоэпизодный случай","short_description":"Несколько классов наблюдений в двух лабораторных эпизодах.","behavior_class":"mixed","difficulty":"expert","tags":["multi-episode","mixed"],"alert":"port_scan","events":4,"variant":"mixed"},
    {"token":"incomplete","case_id":"lab_incomplete_conflicting","display_name":"Неполные и противоречащие сведения","short_description":"Неполный комплект с противоречием состояния источника.","behavior_class":"incomplete_evidence","difficulty":"expert","tags":["incomplete","conflict"],"alert":"auth_failures","events":2,"variant":"conflicting","incomplete":True},
    {"token":"late","case_id":"lab_late_delivery","display_name":"Поздняя доставка событий","short_description":"Порядок доставки отличается от времени наблюдения.","behavior_class":"delivery_anomaly","difficulty":"advanced","tags":["late-delivery","time"],"alert":"beacon","events":3,"variant":"late"},
    {"token":"clocks","case_id":"lab_clock_domains","display_name":"Несколько доменов часов","short_description":"Сопоставление отметок из несогласованных источников времени.","behavior_class":"clock_domain_mismatch","difficulty":"expert","tags":["clock-domain","uncertainty"],"alert":"web_probe","events":2,"variant":"clocks"},
    {"token":"duplicate","case_id":"lab_duplicate_delivery","display_name":"Повторная доставка","short_description":"Повтор события дедуплицируется и не создаёт отдельный факт.","behavior_class":"duplicate_delivery","difficulty":"intermediate","tags":["duplicate","idempotency"],"alert":"port_scan","events":2,"variant":"duplicate"},
    {"token":"equal","case_id":"lab_equal_hypotheses","display_name":"Равноподдержанные гипотезы","short_description":"Несколько объяснений имеют равную поддержку в доступных сведениях.","behavior_class":"equal_support","difficulty":"expert","tags":["hypotheses","equal-support"],"alert":"port_scan","events":2,"variant":"equal"},
)

GAP_NAMES = {
    "missing_event":"Возможное отсутствующее событие", "missing_interval_boundary":"Неизвестная граница временного интервала",
    "clock_domain_mismatch":"Несогласованные источники времени", "insufficient_precision":"Недостаточная точность времени",
    "unresolved_duplicate":"Неустранённый повтор события", "broken_reference":"Неразрешимая ссылка",
    "unexplained_sequence_gap":"Необъяснённый разрыв последовательности", "conflicting_timestamp":"Противоречащие временные отметки",
    "incomplete_episode":"Неполный эпизод", "incomplete_evidence":"Неполный комплект подтверждающих материалов",
}


def _events(spec: dict[str, Any]) -> list[dict[str, Any]]:
    base = 64000 + next(i for i, item in enumerate(CASE_SPECS) if item["case_id"] == spec["case_id"]) * 10
    values = []
    for index in range(spec["events"]):
        alert = spec["alert"]
        if spec["variant"] == "mixed":
            alert = ("port_scan", "web_probe", "auth_failures", "beacon")[index]
        stamp = f"2026-06-{1 + base % 20:02d}T10:00:{index * 3:02d}Z"
        event = make_event(f"v044-r1-seed-{base + index}", alert_class=alert, timestamp=stamp, sequence=index + 1,
                           session="runtime_contract_baseline_001" if index < 2 else "runtime_crash_resume_001",
                           component_status="healthy" if spec["variant"] == "conflicting" and index == 1 else None)
        values.append(event)
    if spec["variant"] == "late":
        values = [values[2], values[0], values[1]]
    if spec["variant"] == "clocks":
        values[1]["event_timestamp"] = values[0]["event_timestamp"]
    if spec["variant"] == "duplicate":
        values.append(copy.deepcopy(values[0]))
    return values


def _iso_add(value: str, milliseconds: int) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    return (dt + timedelta(milliseconds=milliseconds)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _case_view(spec: dict[str, Any], source: dict[str, Any], temporal: dict[str, Any], hypotheses: dict[str, Any]) -> dict[str, Any]:
    card = source["incident_card"]; reconstruction = temporal["temporal_reconstruction"]; analysis = hypotheses["hypothesis_analysis"]
    question_ids = [q["analyst_question_id"] for q in analysis["analyst_questions"]]
    hypothesis_ids = [h["hypothesis_id"] for h in analysis["hypotheses"]]
    timeline = []
    delivery_order = {event["event_id"]: i for i, event in enumerate(source["passive_events"])}
    for index, item in enumerate(card["timeline"]):
        event_id = item["event_ids"][0]; event = next(e for e in source["passive_events"] if e["event_id"] == event_id)
        delay = 4500 if spec["variant"] == "late" and delivery_order[event_id] == 0 else (200 + delivery_order[event_id] * 120)
        clock = "collector_secondary" if spec["variant"] == "clocks" and index else "shadow_event_observation_utc"
        timeline.append({"timeline_item_id":item["timeline_item_id"],"event_id":event_id,"fact_ids":item["fact_ids"],
                         "observation_time":item["start_time"],"delivery_time":_iso_add(item["start_time"],delay),
                         "precision":"second","uncertainty_before_ms":0,"uncertainty_after_ms":999,"clock_domain":clock,
                         "late_delivery":delay >= 4000,"episode":event["runtime_ref"]["session_id"],"subject":event["activity_key"],
                         "fact_type":event["event_type"],"source":"passive_event","ordering_basis":item["ordering_basis"],
                         "explanation":"Положение определяется исходной отметкой наблюдения и её точностью; причинность не выводится.",
                         "limitations":["Время доставки является лабораторной метаданной представления."]})
    gaps = []
    for index, gap in enumerate(reconstruction["gaps"]):
        kind = gap["gap_type"]
        if spec["variant"] == "clocks" and index == 0: kind = "clock_domain_mismatch"
        elif spec["variant"] == "conflicting" and index == 0: kind = "conflicting_timestamp"
        elif spec.get("incomplete") and index == len(reconstruction["gaps"]) - 1: kind = "incomplete_evidence"
        gaps.append({"gap_id":gap["gap_id"],"gap_type":kind,"display_name":GAP_NAMES[kind],"description":gap["effect_on_reconstruction"],
                     "detected_between":gap["detected_between"],"affected_entity_ids":gap["affected_entity_ids"],"basis":gap["basis"],
                     "missing_information":gap["missing_information"],"timeline_effect":"Ограничивает точность или полноту порядка наблюдений.",
                     "affected_hypothesis_ids":hypothesis_ids,"criticality":"high" if kind in {"conflicting_timestamp","incomplete_evidence"} else "medium",
                     "resolvable":gap["resolvable"],"expected_evidence_type":"independent_primary_observation",
                     "question_id":question_ids[index % len(question_ids)] if question_ids else None,"manual_state":"not_reviewed",
                     "limitations":gap["limitations"]})
    nodes = []
    for fact in card["observed_facts"]: nodes.append({"id":fact["fact_id"],"type":"fact","label":fact["predicate"],"source_ids":fact["evidence_ids"]})
    for interval in reconstruction["normalized_intervals"]: nodes.append({"id":interval["interval_id"],"type":"event","label":"Временной интервал","source_ids":interval["source_fact_ids"]})
    for group in reconstruction["correlation_groups"]: nodes.append({"id":group["group_id"],"type":"group","label":"Группа общего источника","source_ids":group["member_fact_ids"]})
    for gap in gaps: nodes.append({"id":gap["gap_id"],"type":"gap","label":gap["display_name"],"source_ids":gap["affected_entity_ids"]})
    for hyp in analysis["hypotheses"]: nodes.append({"id":hyp["hypothesis_id"],"type":"hypothesis","label":hyp["title"],"source_ids":hyp["supporting_assessment_ids"]})
    edges = []
    for relation in reconstruction["fact_relations"] + reconstruction["temporal_relations"]:
        left = relation.get("left_fact_id", relation.get("left_entity_id")); right = relation.get("right_fact_id", relation.get("right_entity_id"))
        edges.append({"id":relation["relation_id"],"type":relation["relation_type"],"left":left,"right":right,"basis":relation.get("relation_basis",relation.get("derivation_basis")),
                      "certainty":relation.get("certainty",relation.get("relation_certainty")),"supporting_fact_ids":relation.get("supporting_fact_ids",[]),
                      "supporting_evidence_ids":relation.get("supporting_evidence_ids",[]),"derived":relation.get("derived",True),"limitations":relation["limitations"],"causal":False})
    for gap in gaps:
        for entity in gap["affected_entity_ids"]:
            edges.append({"id":stable_id("gedge",{"gap":gap["gap_id"],"entity":entity}),"type":"affected_by_gap","left":entity,"right":gap["gap_id"],"basis":gap["basis"],"certainty":"bounded","supporting_fact_ids":gap["affected_entity_ids"],"supporting_evidence_ids":[],"derived":True,"limitations":gap["limitations"],"causal":False})
    assessment_by_id = {x["assessment_id"]:x for x in analysis["evidence_assessments"]}
    for hypothesis in analysis["hypotheses"]:
        for assessment_id in hypothesis["supporting_assessment_ids"] + hypothesis["contradicting_assessment_ids"]:
            assessment = assessment_by_id[assessment_id]
            edges.append({"id":stable_id("hedge",{"hypothesis":hypothesis["hypothesis_id"],"assessment":assessment_id}),"type":assessment["direction"],"left":assessment["source_entity_id"],"right":hypothesis["hypothesis_id"],"basis":assessment["assessment_rule_id"],"certainty":"bounded","supporting_fact_ids":[assessment["source_entity_id"]],"supporting_evidence_ids":[],"derived":True,"limitations":assessment["limitations"],"causal":False})
    comparisons = []
    by_id = {h["hypothesis_id"]: h for h in analysis["hypotheses"]}
    for item in analysis["comparisons"]:
        comparisons.append({**item,"left_name":by_id[item["left_hypothesis_id"]]["title"],"right_name":by_id[item["right_hypothesis_id"]]["title"],
                            "plain_result":{"equally_supported":"Равная поддержка не означает истинность обеих гипотез.","better_supported":"Левая лучше поддержана в доступных сведениях, но не считается истинной.","less_supported":"Правая лучше поддержана в доступных сведениях, но не считается истинной.","incomparable":"Гипотезы нельзя безопасно упорядочить.","insufficient_data":"Данных недостаточно для сопоставления."}.get(item["comparison_result"],"Сопоставление ограничено доступными сведениями.")})
    return {"schema_version":"v0_4_4_console_case_view_v1","case_id":spec["case_id"],"card_id":card["card_id"],"card":card,
            "timeline_modes":["observation","delivery","comparison"],"timeline":timeline,"gaps":gaps,
            "graph":{"modes":["simplified","facts","facts_temporal","facts_structural","gaps","hypotheses","full"],"default_mode":"simplified","nodes":nodes,"edges":edges},
            "hypotheses":analysis["hypotheses"],"assessments":analysis["evidence_assessments"],"comparisons":comparisons,
            "questions":analysis["analyst_questions"],"cross_links":{"facts":len(card["observed_facts"]),"gaps":len(gaps),"hypotheses":len(analysis["hypotheses"]),"comparisons":len(comparisons)},
            "safety":{"laboratory_only":True,"no_final_determination":True,"no_automatic_action":True,"forced_winner":False,"causal_edges":0}}


def build_case(spec: dict[str, Any]) -> dict[str, Any]:
    source = build_bundle(_events(spec), f"v040_v044_{spec['case_id']}", incomplete_evidence=bool(spec.get("incomplete")))
    temporal = build_temporal_bundle(source)
    hypotheses = build_hypothesis_bundle(temporal)
    view = _case_view(spec, source, temporal, hypotheses)
    semantic = sha256_hex(view)
    manifest_seed = {"case_id":spec["case_id"],"files":[
        {"path":"source_bundle.json","sha256":sha256_hex(source)},
        {"path":"temporal_bundle.json","sha256":sha256_hex(temporal)},
        {"path":"hypothesis_bundle.json","sha256":sha256_hex(hypotheses)},
        {"path":"console_case_view.json","sha256":semantic}],"semantic_sha256":semantic}
    manifest = {**manifest_seed,"manifest_id":stable_id("case_manifest",manifest_seed)}
    return {"schema_version":"laboratory_case_bundle_v1","descriptor":{k:v for k,v in spec.items() if k not in {"alert","events","variant","incomplete"}},
            "source_bundle":source,"temporal_bundle":temporal,"hypothesis_bundle":hypotheses,"console_view":view,
            "manifest":manifest,"manifest_sha256":sha256_hex(manifest),"semantic_sha256":semantic,
            "reproducibility":{"seed_namespace":SEED_NAMESPACE,"deterministic":True,"network":False,"backend":False,"model_runtime":False}}


def build_all_cases() -> list[dict[str, Any]]:
    return [build_case(spec) for spec in CASE_SPECS]


class CaseRegistry:
    def __init__(self, report_root: Path = REPORT_CASES) -> None:
        self.report_root = report_root
        self._bundles: dict[str, dict[str, Any]] = {}
        for spec in CASE_SPECS:
            path = report_root / spec["token"] / "laboratory_case_bundle.json"
            self._bundles[spec["token"]] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else build_case(spec)

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(spec["token"] for spec in CASE_SPECS)

    def get(self, token: str) -> dict[str, Any]:
        if token not in self._bundles:
            raise KeyError("unknown_case_token")
        return copy.deepcopy(self._bundles[token])

    def list(self) -> list[dict[str, Any]]:
        rows = []
        for spec in CASE_SPECS:
            bundle = self._bundles[spec["token"]]; view = bundle["console_view"]
            rows.append({**bundle["descriptor"],"card_token":spec["token"],"card_id":view["card_id"],
                         "source_bundle_ids":[bundle["source_bundle"]["manifest"]["bundle_id"],bundle["temporal_bundle"]["temporal_reconstruction"]["reconstruction_id"],bundle["hypothesis_bundle"]["hypothesis_analysis"]["analysis_id"]],
                         "manifest_sha256":bundle["manifest_sha256"],"semantic_sha256":bundle["semantic_sha256"],
                         "expected_fact_count":len(view["card"]["observed_facts"]),"expected_temporal_relation_count":len(bundle["temporal_bundle"]["temporal_reconstruction"]["temporal_relations"]),
                         "expected_fact_relation_count":len(bundle["temporal_bundle"]["temporal_reconstruction"]["fact_relations"]),"expected_gap_count":len(view["gaps"]),
                         "expected_hypothesis_count":len(view["hypotheses"]),"expected_question_count":len(view["questions"]),"expected_review_steps":9,
                         "laboratory_only":True,"enabled":True,"limitations":["Синтетический лабораторный случай; не подтверждает атаку."]})
        return rows

    def catalog_sha256(self) -> str:
        value = {"schema_version":"laboratory_case_catalog_v1","frozen_for_stage":"v0.4.4","cases":self.list()}
        return sha256_hex(value)
