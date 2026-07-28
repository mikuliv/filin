from __future__ import annotations

from typing import Any

from lab_console.cases import CaseRegistry
from lab_console.review import REQUIRED_CHECKS, WORKFLOW_STEPS, ReviewService

SECTION_TITLES = {
    "overview":"Обзор", "facts":"Факты", "timeline":"Временная шкала", "graph":"Граф реконструкции",
    "gaps":"Разрывы", "hypotheses":"Гипотезы", "comparisons":"Матрица сопоставлений",
    "questions":"Вопросы специалисту", "review":"Ручное рассмотрение", "export":"Экспорт",
}


def case_catalog(registry: CaseRegistry, reviews: ReviewService) -> dict[str, Any]:
    rows = []
    for row in registry.list():
        history = reviews.list(row["card_id"]); active = next((x for x in history if x["status"] in {"not_started","in_review","needs_additional_evidence"}), None)
        rows.append({**row,"fact_count":row["expected_fact_count"],"temporal_count":row["expected_temporal_relation_count"],
                     "structural_count":row["expected_fact_relation_count"],"hypothesis_count":row["expected_hypothesis_count"],
                     "gap_count":row["expected_gap_count"],"question_count":row["expected_question_count"],"integrity":"verified",
                     "review_status":active["status"] if active else (history[0]["status"] if history else "not_started"),
                     "last_reviewed_at":history[0]["updated_at"] if history else "—", "review_count":len(history)})
    return {"view_model":"laboratory_case_catalog_v044","cards":rows,"case_count":len(rows),"classes":sorted({x["behavior_class"] for x in rows}),
            "difficulties":["basic","intermediate","advanced","expert"],"catalog_sha256":registry.catalog_sha256()}


def case_page(registry: CaseRegistry, reviews: ReviewService, token: str, section: str) -> dict[str, Any]:
    if section not in SECTION_TITLES: raise KeyError("unknown_case_section")
    bundle = registry.get(token); view = bundle["console_view"]; descriptor = bundle["descriptor"]
    history = reviews.list(view["card_id"]); active = next((x for x in history if x["status"] in {"not_started","in_review","needs_additional_evidence"}), None)
    current = active or (history[0] if history else None)
    progress = reviews.progress(current["review_session_id"]) if current else None
    facts = []
    evidence = {x["evidence_id"]:x for x in view["card"]["evidence_references"]}
    for index, fact in enumerate(view["card"]["observed_facts"], 1):
        facts.append({**fact,"display_ref":f"Факт {index}","sources":[evidence[x] for x in fact["evidence_ids"]],"links":{"timeline":f"/ui/cases/{token}/timeline?focus={fact['fact_id']}","graph":f"/ui/cases/{token}/graph?focus={fact['fact_id']}"}})
    fact_refs = {fact["fact_id"]:fact["display_ref"] for fact in facts}
    gap_type_labels = {
        "missing_interval_boundary":"Неизвестная граница временного интервала",
        "clock_domain_mismatch":"Несогласованные источники времени",
        "conflicting_timestamp":"Противоречащие временные отметки",
        "incomplete_evidence":"Неполный комплект подтверждающих материалов",
    }
    gaps = []
    for gap in view["gaps"]:
        gaps.append({**gap,
                     "type_label":gap_type_labels.get(gap["gap_type"], gap["display_name"]),
                     "detected_between_display":[fact_refs.get(value, "Связанная сущность") for value in gap["detected_between"]],
                     "missing_information_display":"Независимое первичное наблюдение, уточняющее границы интервала",
                     "expected_evidence_label":"Независимое первичное наблюдение",
                     "criticality_label":{"high":"Высокая","medium":"Средняя","low":"Низкая"}.get(gap["criticality"], gap["criticality"]),
                     "manual_state_label":{"not_reviewed":"Не рассмотрен","reviewed":"Рассмотрен"}.get(gap["manual_state"], gap["manual_state"])})
    hypotheses = []
    for index, item in enumerate(view["hypotheses"], 1):
        hypotheses.append({**item,"display_ref":f"H{index}","links":{"graph":f"/ui/cases/{token}/graph?focus={item['hypothesis_id']}","timeline":f"/ui/cases/{token}/timeline?hypothesis={item['hypothesis_id']}","comparisons":f"/ui/cases/{token}/comparisons?hypothesis={item['hypothesis_id']}"}})
    visual_nodes = []
    for index, node in enumerate(view["graph"]["nodes"]):
        visual_nodes.append({**node,"x":75 + (index % 6) * 125,"y":75 + (index // 6) * 120})
    node_map = {x["id"]:x for x in visual_nodes}
    visual_edges = [{**edge,"a":node_map[edge["left"]],"b":node_map[edge["right"]]} for edge in view["graph"]["edges"] if edge["left"] in node_map and edge["right"] in node_map]
    hypothesis_refs = {item["hypothesis_id"]:item["display_ref"] for item in hypotheses}
    gap_by_id = {item["gap_id"]:item for item in gaps}
    question_wording = {
        "missing_interval_boundary": lambda gap, entities: f"Какая первичная запись подтверждает отсутствующую границу интервала для {entities}?",
        "missing_event": lambda gap, entities: f"Есть ли независимая первичная запись события, отсутствующего рядом с {entities}?",
        "clock_domain_mismatch": lambda gap, entities: f"Какой источник времени является опорным и какова измеренная поправка часов для {entities}?",
        "insufficient_precision": lambda gap, entities: f"Есть ли первичная отметка времени с большей точностью для {entities}?",
        "conflicting_timestamp": lambda gap, entities: f"Какая независимая запись позволяет проверить противоречащие отметки времени для {entities}?",
        "unresolved_duplicate": lambda gap, entities: f"Подтверждают ли первичные журналы, что записи для {entities} относятся к одному событию?",
        "broken_reference": lambda gap, entities: f"Какой первичный материал восстанавливает неразрешимую ссылку для {entities}?",
        "incomplete_evidence": lambda gap, entities: f"Какой обязательный первичный материал отсутствует в комплекте для {entities}?",
    }
    questions = []
    for item in view["questions"]:
        linked_gaps = [gap_by_id[value] for value in item["source_gap_ids"] if value in gap_by_id]
        primary_gap = linked_gaps[0] if linked_gaps else None
        entity_labels = [] if primary_gap is None else primary_gap["detected_between_display"]
        entities = ", ".join(entity_labels) if entity_labels else "связанного наблюдения"
        display_question = item["question_text"]
        if primary_gap is not None:
            display_question = question_wording.get(
                primary_gap["gap_type"],
                lambda gap, labels: f"Какие независимые первичные сведения позволяют проверить разрыв «{gap['display_name']}» для {labels}?",
            )(primary_gap, entities)
        gap_labels = [gap["display_name"] for gap in linked_gaps] or ["Разрыв не найден в операторском представлении"]
        questions.append({**item,
                          "display_question":display_question,
                          "purpose":"Закрыть конкретный пробел в доказательствах и проверить, меняется ли относительная опора связанных гипотез.",
                          "expected_label":"Независимая первичная запись, журнал или измерение с проверяемым происхождением.",
                          "source_gap_labels":gap_labels,
                          "related_hypothesis_refs":[hypothesis_refs[value] for value in item["related_hypothesis_ids"] if value in hypothesis_refs],
                          "effect_confirmed_label":"Разрыв можно сузить или закрыть; связанные гипотезы пересматриваются вручную.",
                          "effect_refuted_label":"Разрыв остаётся открытым либо гипотеза, зависящая от ожидаемого факта, ослабляется."})
    result_labels = {"equally_supported":"Опора одинакова","better_supported":"Строка сильнее","less_supported":"Строка слабее","incomparable":"Нельзя сопоставить","insufficient_data":"Мало данных"}
    def decorate_comparison(item: dict[str, Any]) -> dict[str, Any]:
        result = item["comparison_result"]
        left_ref = hypothesis_refs[item["left_hypothesis_id"]]
        right_ref = hypothesis_refs[item["right_hypothesis_id"]]
        explanations = {
            "equally_supported":f"{left_ref} и {right_ref} одинаково поддержаны доступными сведениями. Это не означает, что обе гипотезы верны.",
            "better_supported":f"{left_ref} лучше поддержана доступными сведениями, чем {right_ref}, но не считается доказанной.",
            "less_supported":f"{right_ref} лучше поддержана доступными сведениями, чем {left_ref}, но не считается доказанной.",
            "incomparable":f"{left_ref} и {right_ref} нельзя безопасно упорядочить по доступным сведениям.",
            "insufficient_data":f"Для содержательного сопоставления {left_ref} и {right_ref} недостаточно сведений.",
        }
        decisive_count = len(item.get("decisive_assessment_ids", []))
        unresolved_count = len(item.get("unresolved_difference_ids", []))
        if result == "equally_supported" and decisive_count == 0:
            evidence_summary = "Для этой пары не найдено решающего подтверждения или противоречия, которое выделяло бы одну гипотезу."
        else:
            evidence_summary = f"Решающих оценок: {decisive_count}; неразрешённых различий: {unresolved_count}."
        return {**item,"left_ref":left_ref,"right_ref":right_ref,"result_label":result_labels[result],
                "result_explanation":explanations[result],"evidence_summary":evidence_summary,
                "basis_label":"Сопоставление подтверждений, противоречий и открытых разрывов"}
    pair = {(x["left_hypothesis_id"],x["right_hypothesis_id"]):decorate_comparison(x) for x in view["comparisons"]}
    for item in view["comparisons"]:
        inverse = {**item,"left_hypothesis_id":item["right_hypothesis_id"],"right_hypothesis_id":item["left_hypothesis_id"],"left_name":item["right_name"],"right_name":item["left_name"],"comparison_result":{"better_supported":"less_supported","less_supported":"better_supported"}.get(item["comparison_result"],item["comparison_result"])}
        pair[(item["right_hypothesis_id"],item["left_hypothesis_id"])] = decorate_comparison(inverse)
    matrix = []
    for left in hypotheses:
        cells=[]
        for right in hypotheses:
            cells.append(None if left["hypothesis_id"] == right["hypothesis_id"] else pair.get((left["hypothesis_id"],right["hypothesis_id"])))
        matrix.append({"hypothesis":left,"cells":cells})
    return {"view_model":f"case_{section}_v044","section":section,"section_title":SECTION_TITLES[section],"case_token":token,
            "descriptor":descriptor,"bundle":bundle,"case":view,"facts":facts,"timeline":view["timeline"],"gaps":gaps,
            "graph":{**view["graph"],"nodes":visual_nodes,"edges":visual_edges},"hypotheses":hypotheses,"comparisons":view["comparisons"],"matrix":matrix,"questions":questions,
            "review":current,"review_history":history,"progress":progress,"required_checks":REQUIRED_CHECKS,"workflow_steps":WORKFLOW_STEPS,
            "sections":SECTION_TITLES,"raw":bundle}
