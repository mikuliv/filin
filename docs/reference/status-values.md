---
doc_schema: filin_document_v2
title: Значения статусов
document_type: reference
audience:
  - developer
  - auditor
lifecycle: current
authoritative_for: []
source_of_truth:
  - docs/status/project-status.yaml
  - docs/status/v0_4_track.yaml
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Значения статусов

| Значение | Толкование |
|---|---|
| `completed` | этап завершён, итог определяется отдельным result/policy |
| `passed` | frozen gates этапа пройдены в его scope |
| `negative` / `failed` | один или несколько обязательных gates не пройдены |
| `completed_reassessed` | исторический этап сохранён, поздний аудит ограничил claims |
| `current` | документ или компонент применим к текущей архитектуре |
| `historical` | сохранён для истории, не current execution path |
| `laboratory_only` | подтверждено только в контролируемой лабораторной области |
| `not_reviewed` | operator ещё не зафиксировал рассмотрение item |
| `unresolved` | вопрос остаётся открытым |

`completed` не равно `passed`, а `passed` не равно production ready.
