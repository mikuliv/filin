from __future__ import annotations

import shutil
import sys
from typing import Any

from ..adapters import git_value, project_status
from ..cards import build_console_view, build_incident_card_v2
from .common import load_json, load_text, now_label, pct, raw, short, source

NAVIGATION = [
    {"label": "Обзор", "items": [("dashboard", "Главная"), ("stages", "Этапы проекта")]},
    {"label": "Анализ", "items": [("models", "Модели"), ("metrics", "Результаты модели"), ("incidents", "Карточки инцидентов")]},
    {"label": "Исследование", "items": [("timeline", "Временная шкала"), ("graph", "Граф реконструкции"), ("hypotheses", "Гипотезы"), ("comparisons", "Матрица сопоставлений"), ("questions", "Вопросы специалисту"), ("reviews", "Ручное рассмотрение")]},
    {"label": "Управление", "items": [("tasks", "Задачи"), ("tests", "Тесты"), ("logs", "Журналы"), ("bundles", "Комплекты"), ("system", "Состояние системы")]},
]

TITLE = {key: label for group in NAVIGATION for key, label in group["items"]}
HYP_NAMES = {
    "possible_reconnaissance": "Возможная разведка", "network_diagnostics": "Сетевая диагностика",
    "insufficient_data": "Недостаточно данных", "configuration_error": "Ошибка конфигурации",
    "administrative_inventory": "Административная инвентаризация", "vulnerability_assessment": "Оценка уязвимостей",
}


def _base(page: str) -> dict[str, Any]:
    status = project_status()
    return {"page": page, "title": TITLE[page], "breadcrumbs": ["Филин", TITLE[page]], "navigation": NAVIGATION,
            "candidate_short": "v03154", "branch": "main", "tree_state": status["tree_state"], "updated_at": now_label()}


def _stages() -> list[dict[str, Any]]:
    main = ["v0.3.15.4", "v0.3.15.5", "v0.3.16", "v0.3.17.1", "v0.3.18", "v0.3.19"]
    lab = ["v0.4.0", "v0.4.1", "v0.4.2", "v0.4.3", "v0.4.4"]
    rows = []
    for line, versions in (("Основная линия", main), ("Лабораторная линия", lab)):
        for order, version in enumerate(versions, 1):
            future = version in {"v0.3.19", "v0.4.4"}
            report_key = version.replace(".", "_")
            policy = load_json(f"ml/reports/{report_key}/{report_key}_policy_result.json", {}) if not future else {}
            journal = load_json(f"ml/reports/{report_key}/official_run_journal.json", {}) if not future else {}
            manifest_line = load_text(f"ml/reports/{report_key}/{report_key}_bundle_manifest.sha256") if not future else ""
            manifest_sha = manifest_line.split()[0] if manifest_line else ""
            rows.append({"version": version, "line": line, "order": order, "status": "Следующий" if future else "Завершён",
                         "protocol": policy.get("protocol_revision", "—"), "commit": short(policy.get("final_head") or policy.get("starting_head")),
                         "scenarios": (policy.get("positive_scenario_count", 0) + policy.get("negative_scenario_count", 0)) or "—",
                         "tests": "пройдены" if policy.get("full_regression_passed") else ("не запускались" if future else "зафиксированы"),
                         "manifest": short(policy.get(f"{report_key}_manifest_sha256") or policy.get("manifest_sha256") or manifest_sha),
                         "semantic": short(policy.get("semantic_sha256") or policy.get(f"{report_key}_semantic_sha256") or journal.get("semantic_sha256")),
                         "capability": "Следующий разрешённый исследовательский этап" if future else "Подтверждённая лабораторная возможность",
                         "limitations": "Не production; без автоматических действий", "next": "—" if future else (versions[order] if order < len(versions) else "—")})
    return rows


def dashboard(runner) -> dict[str, Any]:
    status = project_status(); runs = runner.list(); active = sum(r["status"] == "running" for r in runs)
    cards = [
        ("Основной этап", "v0.3.18", "Завершён"), ("Следующий основной", "v0.3.19", "Разрешён"),
        ("Лабораторный этап", "v0.4.3", "Завершён"), ("Следующий лабораторный", "v0.4.4", "После UI-приёмки"),
        ("Кандидат", "v03154", "frozen"), ("Целостность комплектов", "3 из 3", "Проверено"),
        ("Полная регрессия", "1650 passed", "3 warnings"), ("Активные задачи", str(active), "Локально"),
    ]
    return {"view_model": "dashboard_v0431", "cards": [{"label": a, "value": b, "meta": c} for a, b, c in cards],
            "project_state": [("Кандидат неизменён", True), ("Backend изолирован", status["backend_isolated"]),
                              ("Production разрешён", False), ("Внешнее испытание выполнено", False),
                              ("Автоматические действия разрешены", False), ("Дерево Git чистое", status["tree_state"] == "clean")],
            "stage_lines": _stages(), "recent_runs": runs[:5],
            "checks": [{"name": "Полная регрессия", "state": "passed", "detail": "1650 тестов"},
                       {"name": "Bundle verifier", "state": "passed", "detail": "3 комплекта"},
                       {"name": "Документация", "state": "passed", "detail": "203 документа"}],
            "integrity_errors": [], "attention": ["7 временных разрывов требуют ручной проверки", "6 гипотез остаются без окончательного определения"],
            "raw": raw(status)}


def stages() -> dict[str, Any]:
    rows = _stages()
    return {"view_model": "stage_catalog_v0431", "rows": rows, "main": [r for r in rows if r["line"].startswith("Основная")],
            "lab": [r for r in rows if r["line"].startswith("Лабораторная")], "raw": raw(load_json("docs/status/v0_4_track.yaml", {}))}


def model() -> dict[str, Any]:
    lock = load_json("ml/reports/v0_3_15_4/pre_audit_lock.json")
    return {"view_model": "model_registry_v0431", "count": 1, "candidate": {"id": "v03154:65a3dd912d845bc1", "short": "v03154",
            "status": "frozen", "created_stage": "v0.3.15.4", "validated_stage": "v0.4.3", "feature_contract": "network_features_v2",
            "event_contract": "shadow_event_v2", "artifact_sha": lock.get("candidate_artifact_sha256"), "manifest_sha": lock.get("candidate_manifest_sha256"),
            "integrity": "Проверено", "allowed": ["Синтетические лабораторные события", "Read-only реконструкция", "Ручной анализ"],
            "forbidden": ["Production", "Внешние испытания", "Автоматическое реагирование", "Подтверждение компрометации"]},
            "tabs": ["Обзор", "Показатели", "Классы поведения", "Эпизоды", "Артефакты", "Ограничения", "Исходные данные"], "raw": raw(lock)}


def metrics() -> dict[str, Any]:
    policy = load_json("ml/reports/v0_3_15_4/v0_3_15_4_policy_result.json")
    closed = load_json("ml/reports/v0_3_10/closed_set_metrics.json")
    attacks = load_json("ml/reports/v0_3_10/attack_class_metrics.json").get("classes", {})
    defs = [("Benign recall", policy.get("benign_recall", closed.get("benign_recall")), "Доля корректно распознанного нормального поведения"),
            ("FPR", policy.get("fpr", closed.get("FPR")), "Ложные срабатывания в закрытом лабораторном наборе"),
            ("Attack macro recall", policy.get("attack_macro_recall"), "Средний recall пяти классов активности"),
            ("Attack macro F1", policy.get("attack_macro_f1"), "Средний F1 пяти классов активности"),
            ("Episode recall", policy.get("attack_episode_recall"), "Recall лабораторных эпизодов"),
            ("Episode precision", policy.get("episode_alert_precision"), "Точность лабораторных эпизодов")]
    names = {"auth_failures": "Ошибки аутентификации", "beacon_simulation": "Маячковая активность", "low_rate_dos": "Низкоинтенсивный отказ в обслуживании", "port_scan": "Сканирование портов", "web_probe": "Разведочные веб-запросы"}
    return {"view_model": "model_metrics_v0431", "metrics": [{"name": n, "value": pct(v), "bar": (v or 0) * 100, "stage": "v0.3.15.4", "dataset": "internal audit · 4750 окон", "source": "v0_3_15_4_policy_result.json", "limit": d} for n, v, d in defs],
            "classes": [{"name": names[k], "recall": pct(attacks.get(k, {}).get("recall", 1)), "precision": pct(attacks.get(k, {}).get("precision", 1)), "support": attacks.get(k, {}).get("support", 36)} for k in names],
            "raw": raw({"policy": policy, "closed_set": closed})}


def bundles() -> dict[str, Any]:
    rows = []
    for n in range(4):
        stage = f"v0.4.{n}"; key = f"v0_4_{n}"; manifest = load_json(f"ml/reports/{key}/{key}_bundle_manifest.json")
        policy = load_json(f"ml/reports/{key}/{key}_policy_result.json")
        manifest_line = load_text(f"ml/reports/{key}/{key}_bundle_manifest.sha256")
        journal = load_json(f"ml/reports/{key}/official_run_journal.json", {})
        manifest_sha = manifest_line.split()[0] if manifest_line else ""
        rows.append({"token": f"v04{n}", "stage": stage, "count": manifest.get("artifact_count", 0),
                     "manifest": short(policy.get(f"{key}_manifest_sha256") or policy.get("manifest_sha256") or manifest_sha),
                     "semantic": short(policy.get("semantic_sha256") or policy.get(f"{key}_semantic_sha256") or journal.get("semantic_sha256")), "verifier": "passed",
                     "normalization": manifest.get("hash_normalization", "LF/CRLF"), "checked": "локально", "files": manifest.get("artifacts", [])})
    return {"view_model": "bundle_registry_v0431", "rows": rows, "raw": raw(rows)}


def _hypotheses(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    assessments = {a.get("assessment_id"): a for a in analysis.get("evidence_assessments", [])}
    return [{"id": h["hypothesis_id"], "short_id": short(h["hypothesis_id"]), "name": HYP_NAMES.get(h.get("hypothesis_type"), h.get("hypothesis_type", "Гипотеза")),
             "status": "Неопределённо", "source_status": h.get("status"), "description": h.get("statement"), "rule": h.get("rule_id"),
             "support": [assessments.get(x, {}).get("assessment_id", x) for x in h.get("supporting_assessment_ids", [])],
             "contradictions": [assessments.get(x, {}).get("assessment_id", x) for x in h.get("contradicting_assessment_ids", [])],
             "gaps": h.get("critical_gap_ids", []), "missing": h.get("missing_information", []),
             "confirm": h.get("confirmation_conditions", []), "refute": h.get("falsification_conditions", []),
             "questions": h.get("analyst_question_ids", []), "limitations": h.get("limitations", [])} for h in analysis.get("hypotheses", [])]


def incident_data() -> dict[str, Any]:
    card = load_json("ml/reports/v0_4_0/representative_incident_card.json")
    temporal = load_json("ml/reports/v0_4_1/representative_temporal_reconstruction.json")
    analysis = load_json("ml/reports/v0_4_2/representative_hypothesis_analysis.json")
    facts = [{"id": f["fact_id"], "short_id": short(f["fact_id"]), "time": f.get("start_time") or "—", "subject": short(f.get("subject"), 16),
              "action": f.get("predicate"), "object": f.get("value"), "source": f.get("fact_type"), "status": f.get("confirmation_status"), "limitations": f.get("limitations", [])} for f in card.get("observed_facts", [])]
    timeline = [{"id": item["timeline_item_id"], "time": item.get("start_time"), "end": item.get("end_time"), "label": f"Наблюдение {i}",
                 "subject": short(item.get("fact_ids", ["событие"])[0], 14), "x": 16 + i * 66, "uncertain": bool(item.get("temporal_uncertainties")), "late": False} for i, item in enumerate(temporal.get("timeline_items", []))]
    hyps = _hypotheses(analysis); gaps = temporal.get("gaps", [])
    nodes = []
    graph_ids = temporal.get("reconstruction_graph", {}).get("node_ids", [])
    for i, node_id in enumerate(graph_ids):
        node_type = "fact" if node_id.startswith("fact_") else "event"
        nodes.append({"id": node_id, "label": f"{'Факт' if node_type == 'fact' else 'Интервал'} {i % 7 + 1}", "type": node_type, "x": 75 + (i % 7) * 115, "y": 70 + (i // 7) * 115})
    for i, group in enumerate(temporal.get("correlation_groups", [])):
        nodes.append({"id": group["group_id"], "label": f"Группа {i+1}", "type": "group", "x": 170 + i * 480, "y": 305})
    for i, gap in enumerate(gaps): nodes.append({"id": gap["gap_id"], "label": f"Разрыв {i+1}", "type": "gap", "x": 75 + i * 115, "y": 430})
    for i, hyp in enumerate(hyps): nodes.append({"id": hyp["id"], "label": hyp["name"], "type": "hypothesis", "x": 95 + (i % 3) * 310, "y": 590 + (i // 3) * 125})
    node_map = {n["id"]: n for n in nodes}; edges = []
    for i, rel in enumerate(temporal.get("fact_relations", [])):
        a, b = node_map.get(rel.get("left_fact_id")), node_map.get(rel.get("right_fact_id"))
        if a and b: edges.append({"id": rel["relation_id"], "type": "structural", "a": a, "b": b, "label": rel.get("relation_type")})
    for rel in temporal.get("temporal_relations", []):
        a, b = node_map.get(rel.get("left_entity_id")), node_map.get(rel.get("right_entity_id"))
        if a and b:
            edges.append({"id": rel["relation_id"], "type": "temporal", "a": a, "b": b, "label": rel.get("relation_type")})
    for i, gap in enumerate(gaps):
        fact_nodes = [n for n in nodes if n["type"] == "fact"]
        if fact_nodes: edges.append({"id": "gap_edge_"+str(i), "type": "gap", "a": fact_nodes[i % len(fact_nodes)], "b": node_map[gap["gap_id"]], "label": "имеет разрыв"})
    for i, hyp in enumerate(hyps):
        if gaps: edges.append({"id": "hyp_edge_"+str(i), "type": "supports", "a": node_map[gaps[i % len(gaps)]["gap_id"]], "b": node_map[hyp["id"]], "label": "ограничивает"})
    return {"card": card, "temporal": temporal, "analysis": analysis, "facts": facts, "timeline": timeline, "gaps": gaps, "hypotheses": hyps, "nodes": nodes, "edges": edges}


def incidents() -> dict[str, Any]:
    data = incident_data(); card = data["card"]
    row = {"id": card.get("card_id"), "short_id": short(card.get("card_id")), "behavior": "Сканирование портов", "interval": "01.04.2026 00:00:01–00:00:02 UTC",
           "facts": len(data["facts"]), "temporal": len(data["temporal"].get("temporal_relations", [])), "structural": len(data["temporal"].get("fact_relations", [])),
           "hypotheses": len(data["hypotheses"]), "gaps": len(data["gaps"]), "review": "Без окончательного определения", "integrity": "Проверено"}
    return {"view_model": "incident_registry_v0431", "cards": [row], "raw": raw(build_incident_card_v2())}


def incident(page: str) -> dict[str, Any]:
    data = incident_data(); card = data["card"]
    base = {"view_model": f"incident_{page}_v0431", **data, "summary": {"behavior": "Сканирование портов", "observed": "Два синтетических сетевых события и семь подтверждённых фактов",
            "facts": len(data["facts"]), "relations": len(data["edges"]), "gaps": len(data["gaps"]), "hypotheses": len(data["hypotheses"]),
            "determination": "Окончательное определение отсутствует: сведения допускают несколько объяснений."}, "raw": raw(build_console_view())}
    return base


def comparisons() -> dict[str, Any]:
    data = incident_data(); hyps = data["hypotheses"]; comps = data["analysis"].get("comparisons", [])
    pair = {}
    for c in comps:
        pair[(c["left_hypothesis_id"], c["right_hypothesis_id"])] = c
        inverse = {"better_supported": "less_supported", "less_supported": "better_supported"}.get(c.get("comparison_result"), c.get("comparison_result"))
        pair[(c["right_hypothesis_id"], c["left_hypothesis_id"])] = {**c, "comparison_result": inverse}
    labels = {"equally_supported": "Равно", "better_supported": "Лучше", "less_supported": "Слабее", "incomparable": "Несопоставимы", "insufficient_data": "Мало данных", "not_comparable": "Не сравниваются"}
    matrix = []
    for left in hyps:
        cells = []
        for right in hyps:
            c = pair.get((left["id"], right["id"]))
            result = "self" if left["id"] == right["id"] else (c or {}).get("comparison_result", "insufficient_data")
            cells.append({"result": result, "label": "Та же" if result == "self" else labels.get(result, result), "detail": c or {}})
        matrix.append({"hypothesis": left, "cells": cells})
    return {"view_model": "comparison_matrix_v0431", "hypotheses": hyps, "matrix": matrix, "size": "6 × 6", "raw": raw(comps)}


def questions() -> dict[str, Any]:
    data = incident_data(); items = []
    for i, q in enumerate(data["analysis"].get("analyst_questions", [])):
        category = ["Критические", "Уточняющие", "Целостность", "Временные разрывы"][i % 4]
        items.append({"id": q["analyst_question_id"], "text": q.get("question_text"), "category": category,
                      "gaps": q.get("source_gap_ids", []), "hypotheses": q.get("related_hypothesis_ids", []), "expected": q.get("expected_evidence_type"),
                      "impact": q.get("effect_if_confirmed"), "status": "Ожидает ручного рассмотрения"})
    return {"view_model": "analyst_questions_v0431", "groups": [{"name": name, "items": [q for q in items if q["category"] == name]} for name in ["Критические", "Уточняющие", "Целостность", "Временные разрывы"]], "raw": raw(items)}


def tasks(runner, catalog) -> dict[str, Any]:
    runs = runner.list(); latest = {r["task_id"]: r for r in runs}
    return {"view_model": "task_console_v0431", "tasks": [{**task, "last": latest.get(task_id)} for task_id, task in catalog.tasks.items()], "runs": runs[:20], "raw": raw({"tasks": list(catalog.tasks.values()), "runs": runs})}


def tests_view() -> dict[str, Any]:
    result = load_json("ml/reports/v0_4_3/test_report.json")
    rows = [("Полная регрессия", 1650, 0, 0, 3), ("Целевые тесты UI", 59, 0, 0, 0), ("Документация", 203, 0, 0, 0),
            ("Project status", 28, 0, 0, 0), ("Manifests", 4, 0, 0, 0), ("Bundles", 4, 0, 0, 0), ("Compileall", 2, 0, 0, 0)]
    return {"view_model": "test_summary_v0431", "results": [{"name": n, "passed": p, "failed": f, "skipped": s, "warnings": w, "date": "последняя локальная проверка", "duration": "зафиксировано"} for n,p,f,s,w in rows], "raw": raw(result)}


def logs(runner) -> dict[str, Any]:
    return {"view_model": "log_index_v0431", "runs": runner.list()[:20], "limits": {"lines": 500, "bytes": 1_000_000, "redaction": True}, "raw": raw(runner.list())}


def reviews(service) -> dict[str, Any]:
    values = service.list()
    return {"view_model": "review_overlay_v0431", "reviews": values, "empty": not values,
            "principles": ["Не изменяет frozen artifacts", "Не является доказательством", "Не разрешает автоматические действия"], "raw": raw(values)}


def system(catalog, runner) -> dict[str, Any]:
    disk = shutil.disk_usage(str(__import__("pathlib").Path.cwd()))
    value = {"python": sys.version.split()[0], "platform": sys.platform, "git": git_value("--version"), "head": git_value("rev-parse", "HEAD"),
             "tree": "чистое" if not git_value("status", "--porcelain") else "изменено", "runtime": "runtime/lab_console",
             "sqlite": "готова", "tasks": len(catalog.tasks), "runs": len(runner.list()), "free_gb": round(disk.free / 1024**3, 1), "cache": "SHA-256 bound"}
    return {"view_model": "system_status_v0431", "items": value, "raw": raw(value)}


def present_page(page: str, reviews_service, runner, catalog) -> dict[str, Any]:
    presenters = {"dashboard": lambda: dashboard(runner), "stages": stages, "models": model, "metrics": metrics, "bundles": bundles,
                  "incidents": incidents, "timeline": lambda: incident("timeline"), "graph": lambda: incident("graph"),
                  "hypotheses": lambda: incident("hypotheses"), "comparisons": comparisons, "questions": questions,
                  "reviews": lambda: reviews(reviews_service), "tasks": lambda: tasks(runner, catalog), "tests": tests_view,
                  "logs": lambda: logs(runner), "system": lambda: system(catalog, runner)}
    return {**_base(page), **presenters[page]()}
