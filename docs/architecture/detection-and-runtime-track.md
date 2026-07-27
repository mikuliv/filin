---
doc_schema: filin_document_v2
title: Основная линия обнаружения и runtime
document_type: architecture
audience:
  - developer
  - auditor
lifecycle: current
authoritative_for:
  - v0_3_architecture
source_of_truth:
  - docs/status/project-status.yaml
  - collectors/shadow/contracts/candidate_registry_v1.json
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Основная линия обнаружения и runtime

## Входы

Контролируемые PCAP и журналы Zeek, соответствующие методологии конкретной
кампании. Произвольный production capture не является разрешённым входом.

## Обработка

`collectors/` нормализуют наблюдения, `ml/features/` применяет
`network_features_v2`, а candidate registry разрешает только зафиксированный
кандидат `v03154:65a3dd912d845bc1`. Episode policy допускает отказ от определённого
класса. `shadow_event_v2` переносит решение в пассивный runtime contract.

## Доставка

`staging/` и `rehearsal/` подтверждают только изолированный локальный transport.
Эталонный receiver не является production backend. External integration остаётся
запрещённой.

## Текущая граница

Завершён `v0.3.18`; следующий `v0.3.19` ограничен review frozen package и
согласованием trial plan. Полная история находится в
[основной линии](../status/mainline-history.md).
