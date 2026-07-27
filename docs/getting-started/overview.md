---
doc_schema: filin_document_v2
title: Обзор для нового читателя
document_type: overview
audience:
  - newcomer
lifecycle: current
authoritative_for: []
source_of_truth:
  - docs/status/current-status.md
  - docs/architecture/overview.md
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Обзор для нового читателя

## Назначение

«Филин» исследует воспроизводимый путь от сетевого наблюдения до безопасного
ручного аналитического рассмотрения. Платформа сочетает зафиксированную модель,
пассивный локальный runtime, проверяемую реконструкцию и лабораторную консоль.

## Две линии

Основная линия `v0.3.x` отвечает за данные, признаки, кандидата, runtime и внешнюю
процедуру. Лабораторная `v0.4.x` потребляет неизменные события и строит факты,
отношения, gaps, hypotheses и карточки. Завершены соответственно `v0.3.18` и
`v0.4.4`; следующие допустимые этапы — `v0.3.19` и `v0.4.5`.

## Что читать дальше

1. [Текущий статус](../status/current-status.md).
2. [Архитектура](../architecture/overview.md).
3. [Подтверждённые возможности](../status/confirmed-capabilities.md).
4. [Ограничения](../architecture/limitations.md).
5. [Глоссарий](../reference/glossary.md).

Ключевая формулировка: лабораторная работоспособность подтверждена, внешняя
применимость пока не подтверждена.
