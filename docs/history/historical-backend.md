---
doc_schema: filin_document_v2
title: Исторический backend prototype
document_type: history
audience:
  - developer
  - auditor
lifecycle: historical
authoritative_for: []
source_of_truth:
  - backend
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Исторический backend prototype

`backend/` — ранний демонстрационный API и набор incident endpoints. Он полезен для
истории интерфейсов и unit tests, но не входит в текущий проверенный путь.

Текущий transport заканчивается эталонным локальным receiver, а лабораторное
рассмотрение выполняет `lab_console/`. Ни один из них не является production backend.

Старый [incident workflow](../incident-workflow.md) сохранён как redirect.
