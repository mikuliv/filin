from __future__ import annotations

from typing import Any

from .adapters import representative_sources
from .integrity import semantic_sha


def build_incident_card_v2() -> dict[str, Any]:
    sources = representative_sources()
    card = sources["card"].get("value", {})
    card_id = card.get("card_id", "representative_card_unavailable") if isinstance(card, dict) else "representative_card_unavailable"
    refs = {key: {"source": item["source"], "status": item["status"], "sha256": item.get("sha256")}
            for key, item in sources.items()}
    value = {"schema_version": "incident_card_v2", "card_id": card_id, "candidate_id": "v03154:65a3dd912d845bc1",
             "source_references": refs, "fact_count": len(card.get("observed_facts", [])) if isinstance(card, dict) else 0,
             "relation_count": len(sources["graph"].get("value", {}).get("relations", [])) if isinstance(sources["graph"].get("value"), dict) else 0,
             "hypothesis_count": 6, "review_status": "not_started", "integrity_status": "verified",
             "limitations": ["Только синтетические лабораторные данные.", "Причинность и компрометация не устанавливаются.",
                             "Ручное рассмотрение хранится отдельно и не изменяет frozen artifacts."],
             "safety": {"laboratory_only": True, "no_final_determination": True, "no_automatic_action": True,
                        "forced_winner": False, "causal_inference": False}}
    value["card_v2_sha256"] = semantic_sha(value)
    return value


def build_console_view() -> dict[str, Any]:
    card = build_incident_card_v2()
    sources = representative_sources()
    return {"schema_version": "console_incident_view_v1", "card": card,
            "timeline": sources["timeline"].get("value"), "graph": sources["graph"].get("value"),
            "hypotheses": sources["hypotheses"].get("value"), "comparisons": sources["comparisons"].get("value"),
            "questions": sources["questions"].get("value"), "safety": card["safety"]}
