# Документация платформы «Филин»

Этот индекс — основная навигационная точка. Machine-readable статус хранится в
[`status/project-status.yaml`](status/project-status.yaml), а краткое объяснение
— в [current status](status/current-status.md).

## Начало работы

- [Обзор](getting-started/overview.md) — безопасный маршрут нового читателя.
- [Локальное окружение](getting-started/local-environment.md) — зависимости и
  границы runtime.
- [Тестирование](getting-started/testing.md) — unit, regression, documentation
  и bundle gates.
- [Структура репозитория](getting-started/repository-layout.md) — назначение
  tracked и runtime-only каталогов.

## Архитектура

- [Обзор](architecture/overview.md) — current pipeline и простая схема.
- [Поток данных](architecture/data-flow.md) — путь observations и evidence.
- [Detection pipeline](architecture/detection-pipeline.md) — causal features и
  frozen inference.
- [Stateful processing](architecture/stateful-processing.md) — episode semantics.
- [Passive events](architecture/passive-events.md) — versioned события без
  полномочий на воздействие.
- [Delivery runtime](architecture/delivery-runtime.md) — staging transport и
  local verified sink.
- [Trust boundaries](architecture/trust-boundaries.md) — изоляция ролей,
  labels, runtime и evidence.
- [Ограничения](architecture/limitations.md) — неподтверждённые возможности.

## Исследовательская методология

- [Методология](research/methodology.md) — development/evaluation separation.
- [Causal features](research/causal-features.md) — причинные ограничения.
- [Candidate lineage](research/candidate-lineage.md) — current frozen identity.
- [Принципы оценки](research/evaluation-principles.md) — scientific и runtime
  gates.
- [Uncertainty и abstention](research/uncertainty-and-abstention.md) — coverage
  semantics.
- [Воспроизводимость](research/reproducibility.md) — immutable evidence и Git
  HEAD terminology.

## Текущий статус

- [Current status](status/current-status.md) — единый human-readable статус.
- [Confirmed capabilities](status/confirmed-capabilities.md) — только
  evidence-backed claims.
- [Prohibited capabilities](status/prohibited-capabilities.md) — явные запреты.
- [Следующий этап](status/next-stage.md) — scope v0.3.19.
- [Version history](status/version-history.md) — полная история результатов.
- [Roadmap](roadmap.md) — разрешённый шаг и долгосрочные направления.

## Контракты

- [Индекс contracts](contracts/index.md) — passive event, delivery, timing и
  external-review contracts.

## Экспериментальные протоколы

- [Индекс protocols](protocols/index.md) — навигация к frozen stage protocols.

## Итоговые отчёты

- [Индекс reports](reports/index.md) — aggregate evidence по версиям.
- [Эксперименты](experiments.md) — chronological research overview.

## Внешняя проверка

- [External review overview](external_review/README.md) — design-only package
  v0.3.18.
- [Reviewer guide](external_review/reviewer_guide.md) — порядок независимой
  проверки.
- [Known limitations](external_review/known_limitations.md) — границы package.

## История и корректировки

- [Stage timeline](history/stage-timeline.md) — укрупнённая последовательность.
- [Корректировки и отрицательные результаты](history/corrections-and-negative-results.md)
  — сохранённые failures и reassessments.
- [Архивная документация](history/archived-documentation.md) — superseded
  overview и redirect notes.
- [Historical audits](audits/) — сохранённые integrity материалы.

## Разработка документации

- [Стиль и терминология](contributing/documentation-style.md) — единые термины и
  правила claims.
- [Testing and validation](contributing/testing-and-validation.md) — обязательные
  documentation gates.
- [Инвентаризация](audit/documentation_inventory.md) — исходное состояние
  maintenance pass.
- [Итоговый отчёт переработки](audit/documentation_refactor_report.md) —
  результаты и ограничения.
