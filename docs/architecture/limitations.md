---
doc_schema: filin_document_v2
title: Текущие ограничения платформы
document_type: architecture
audience:
  - newcomer
  - developer
  - operator
  - auditor
lifecycle: current
authoritative_for:
  - current_platform_limitations
source_of_truth:
  - docs/status/project-status.yaml
  - docs/status/v0_4_track.yaml
  - stage_policy_results
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Текущие ограничения платформы

## Доказательная область

Проверки выполнены в контролируемых и синтетических средах. Внешняя организация,
реальные независимые данные и blind labels пока не участвовали. Поэтому качество
и надёжность нельзя переносить на произвольную инфраструктуру.

## Модель

Candidate зафиксирован и не адаптируется к новой среде. Conformal set и abstention
ограничивают вывод, но не доказывают корректность класса. Unknown и малые выборки
могут приводить к неопределённому решению.

## Runtime

Подтверждён изолированный локальный transport. Production backend, публичная сеть,
реальные уведомления и automatic response запрещены. Исторический backend не
входит в текущий путь.

## Реконструкция

Факты зависят от доступных evidence references. Неизвестные интервалы, clock-domain
differences и неполные материалы представлены gaps. Temporal/structural relations
не являются доказательством причинности.

## Гипотезы

Hypothesis comparison отражает относительную опору в доступных сведениях.
`equally_supported` не означает истинность обеих гипотез, а `better_supported` —
истинность одной. Forced winner отсутствует намеренно.

## Консоль и review

Консоль работает только локально. Каталог v0.4.4 состоит из 12 синтетических
случаев. Notes, progress и decisions сохраняются в отдельном SQLite overlay и не
становятся evidence. Export не является юридическим или криминалистическим заключением.

## Внешняя процедура

`v0.3.18` подготовил frozen package и синтетическую rehearsal, но не провёл trial.
`v0.3.19` допускает только независимый review и согласование будущего плана.

Исторические ограничения сохранены в [отдельной хронике](../history/historical-limitations.md),
а нормативные запреты — в [каноническом списке](../status/prohibited-capabilities.md).
