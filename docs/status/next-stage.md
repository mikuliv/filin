---
doc_schema: filin_document_v2
title: Следующие допустимые этапы
document_type: status
audience:
  - developer
  - auditor
  - external_reviewer
lifecycle: current
authoritative_for:
  - next_stage_summary
source_of_truth:
  - docs/status/project-status.yaml
  - docs/status/v0_4_track.yaml
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Следующие допустимые этапы

## Основная линия: v0.3.19

Разрешена только независимая экспертная проверка frozen package v0.3.18 и
согласование плана возможного будущего испытания. Передача реальных данных,
подключение к инфраструктуре и фактическое испытание требуют отдельного решения.

## Лабораторная линия: v0.4.5

Разрешён только новый заранее определённый лабораторный этап. `v0.4.5` не
реализован и не начат. Он не может изменять frozen evidence предшествующих этапов
или подменять основную линию `v0.3.19`.

## Неизменяемая граница

Documentation Maintenance v2 не является ни `v0.3.19`, ни `v0.4.5`. Этот проход
не изменяет кандидата, модель, runtime contracts, научные результаты или разрешения.

Проверяемые источники: [project-status.yaml](project-status.yaml) и
[v0_4_track.yaml](v0_4_track.yaml).
