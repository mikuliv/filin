---
doc_schema: filin_document_v2
title: Текущий статус проекта
document_type: status
audience:
  - newcomer
  - developer
  - auditor
lifecycle: current
authoritative_for:
  - human_readable_project_status
source_of_truth:
  - docs/status/project-status.yaml
  - docs/status/v0_4_track.yaml
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
latest_completed_stage: v0.3.18
latest_stage_status: completed
latest_stage_result: passed
next_allowed_stage: v0.3.19
next_stage_scope: external_package_review_only
external_trial_execution_allowed: false
shadow_mode_allowed: false
backend_integration_allowed: false
production_ready: false
automatic_enforcement_ready: false
real_external_data_used_in_v0_3_18: false
synthetic_rehearsal_scientific_evidence: false
---

# Текущий статус проекта

Machine-readable реестры имеют приоритет над этой сводкой. Проект ведёт две
доказательно разделённые линии.

| Линия | Последний этап | Результат | Следующий этап | Ограничение |
|---|---|---|---|---|
| Основная `v0.3.x` | `v0.3.18` | Frozen external-review package подготовлен; синтетическая репетиция процедуры пройдена | `v0.3.19` — только независимая проверка пакета и согласование плана будущего испытания | Реальные внешние данные, метки и организация не участвовали; фактическое испытание не разрешено |
| Лабораторная `v0.4.x` | `v0.4.4` | Сохраняемый операторский цикл подтверждён на 12 независимых синтетических карточках | `v0.4.5` — отдельный заранее определённый лабораторный этап | Внешняя применимость, production, backend и автоматические действия не подтверждены |

## Общие якоря

- кандидат: `v03154:65a3dd912d845bc1`;
- contract признаков: `network_features_v2`;
- внешний статус модели: не подтверждён;
- промышленная готовность: `false`;
- пассивный режим в реальной инфраструктуре: `false`;
- автоматическое воздействие: `false`.

## Связь линий

`v0.4.x` потребляет неизменяемые пассивные события основной линии и строит над
ними лабораторные факты, отношения, разрывы, гипотезы и операторскую карточку.
Эта линия не меняет модель, не заменяет `v0.3.19` и не является внешней научной
проверкой кандидата.

## Точное толкование v0.3.18

Этап завершил проектирование процедуры, контракты ролей, frozen package и
синтетическую репетицию. Он не проводил слепое испытание на данных независимой
организации. Разрешён только следующий организационно-проверочный шаг `v0.3.19`.

## Точное толкование v0.4.4

Этап подтвердил локальный каталог из 12 случаев, объяснимые представления
timeline/graph/gaps/hypotheses, сохраняемое ручное рассмотрение и детерминированный
экспорт. Результат относится только к предусмотренным синтетическим лабораторным
случаям и не устанавливает истинность гипотез.

## Источники

- [project-status.yaml](project-status.yaml) — основная линия;
- [v0_4_track.yaml](v0_4_track.yaml) — лабораторная линия;
- [источники истины](../reference/sources-of-truth.md);
- [следующие этапы](next-stage.md);
- [подтверждённые возможности](confirmed-capabilities.md);
- [запрещённые возможности](prohibited-capabilities.md).
