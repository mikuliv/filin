---
doc_schema: filin_document_v2
title: Индекс экспериментальных этапов
document_type: history
audience:
  - researcher
  - auditor
lifecycle: current
authoritative_for:
  - experiment_navigation
source_of_truth:
  - docs/status/project-status.yaml
  - docs/status/v0_4_track.yaml
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Индекс экспериментальных этапов

Эта страница даёт краткую навигацию. Полные metrics, gates и limitations остаются
в stage-specific frozen reports.

## Ранние эксперименты

`v0.3.1–v0.3.10.1`: baseline, robustness, environment shift, training cycles,
uncertainty и audits. Результаты включают отрицательные stages и не определяют
текущий статус напрямую.

## Формирование кандидата

`v0.3.11–v0.3.15.5.1`: burden-aware model, causal corrections, prospective
environment, runtime trials, controlled redevelopment, independent holdout и
candidate-compatible recovery. Текущий candidate сформирован в `v0.3.15.4`.

## Runtime, transport и длительная кампания

`v0.3.16–v0.3.17.1`: isolated staging transport, long local rehearsal и corrective
audit. [v0.3.16](experiments/v0_3_16.md), [v0.3.17](experiments/v0_3_17.md),
[v0.3.17.1](experiments/v0_3_17_1.md).

## Внешняя процедура

`v0.3.18`: frozen external-review package и synthetic rehearsal, но не real trial.
[Описание этапа](experiments/v0_3_18.md).

## Реконструкция и гипотезы

- [v0.4.0](experiments/v0_4_0.md) — incident reconstruction;
- [v0.4.1](experiments/v0_4_1.md) — temporal reconstruction;
- [v0.4.2](experiments/v0_4_2.md) — structural relations и hypotheses.

## Консоль и операторский цикл

- [v0.4.3](experiments/v0_4_3.md) — localhost console;
- [v0.4.3.1](experiments/v0_4_3_1.md) — UI revision;
- [v0.4.4 summary](../ml/reports/v0_4_4/summary.md) — 12 cases и persistent review.

Полные навигационные таблицы: [protocols](protocols/index.md) и [reports](reports/index.md).
