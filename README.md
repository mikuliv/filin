# Платформа «Филин»

Машиночитаемый источник статуса: [`docs/status/project-status.yaml`](docs/status/project-status.yaml). Общий индекс: [`docs/index.md`](docs/index.md).

## 1. Назначение

«Филин» — исследовательская платформа для воспроизводимого анализа сетевых наблюдений в изолированной лаборатории. Она строит causal 51-feature представление, применяет замороженный классификатор и формирует пассивные события для последующего анализа.

## 2. Текущий проверенный статус

Последний завершённый этап — v0.3.15.1. Корректирующий аудит усилил passive exporter, но не подтвердил историческую готовность к v0.3.16: новый этап подготовки staging connector пока заблокирован. Production, shadow mode, backend integration и автоматические действия запрещены.

## 3. Что представляет собой «Филин»

Проект объединяет безопасный лабораторный стенд, capture и Zeek-обработку, построение признаков, frozen inference, stateful episode policy, passive event contract и локальный доказательный runtime. Это исследовательский код, а не готовое средство защиты.

## 4. Границы проекта

Подтверждения относятся к контролируемым локальным сценариям. Проект не проходил внешнюю организационную validation, не подключён к действующей инфраструктуре и не имеет полномочий изменять сеть.

## 5. Архитектура

Основные слои: `lab` для изолированных сценариев, `collectors` для capture и passive runtime, `ml` для frozen research pipeline, `tools` для аудита, `docs` для контрактов и статуса. Исторический `backend` не интегрирован с сенсором.

## 6. Поток обработки

Контролируемый трафик → PCAP → Zeek logs → causal feature window → frozen candidate → stateful decision → `shadow_event_v1` → durable spool → bounded priority queue → rate limiter → local sink → ACK → checkpoint → reconciliation.

## 7. Подсистема обнаружения

Текущий frozen candidate создан на v0.3.11. v0.3.15.1 не выполняет fit, calibration fit, conformal fit, feature selection, threshold selection или новый inference исторических окон.

## 8. Поддерживаемые классы наблюдаемого поведения

Лабораторный closed set включает benign, port scan, authentication failures, web probe, low-rate DoS и beacon-like behavior. Эти имена описывают классы синтетического стенда, а не подтверждённую атрибуцию реальных атак.

## 9. Stateful-обработка эпизодов

Episode state различает benign, pending, review, alert и post-alert continuation. Deduplication подавляет повторные доставки по idempotency key; она не меняет frozen prediction или causal state.

## 10. Passive event contract

[`shadow_event_v1`](docs/contracts/shadow-event-v1.md) задаёт allowlist полей, deterministic identity, hash и отсутствие action authority. Схема исторически неизменна.

## 11. Надёжность доставки

Исправленный v0.3.15.1 runtime реализует единый at-least-once path: validation, canonical serialization, durable fsync spool, priority queue, token bucket, batch delivery, строгий ACK, bounded retry, atomic checkpoint, compaction и restart recovery. Exactly-once не заявляется; semantic deduplication выполняет локальный sink.

## 12. Безопасность и fail-safe ограничения

Runtime использует только локальные fixtures и mock sink. Любой неизвестный fault-сценарий завершается `unsupported`, malformed/unknown ACK не считается успехом, а непроверенная целостность блокирует resume и readiness.

## 13. Текущий frozen candidate

Candidate ID: `v0311:19176acb401be2d4`. Он был создан на v0.3.11 и не изменялся на v0.3.12–v0.3.15.1.

## 14. Последний независимый holdout

v0.3.13 — независимый prospective environmental holdout. Его научный результат не отменён переоценкой runtime-утверждений v0.3.14/v0.3.15.

## 15. Последний runtime trial

v0.3.15 — controlled local passive shadow trial. Immutable bundle и scientific predictions сохранены. Аудит v0.3.15.1 установил, что исходная реализация delivery faults не доказывала полный integrated fault path, поэтому прежнее решение о переходе к v0.3.16 не подтверждено.

## 16. Подтверждённые возможности

- локальная causal feature extraction и frozen inference;
- independent holdout v0.3.13;
- immutable bundle v0.3.15;
- исправленный integrated passive exporter v0.3.15.1;
- поведенческие fault, crash, resume, drop, privacy и performance tests;
- source/sink reconciliation на локальных immutable событиях.

## 17. Неподтверждённые возможности

- эксплуатационная точность в реальной организации;
- production capture и online deployment;
- backend или SIEM integration;
- shadow mode с реальным получателем;
- automatic enforcement;
- внешняя security и privacy validation.

## 18. Хронология этапов

<!-- stage-history:start -->
- v0.3.1 — базовая оценка.
- v0.3.2 — robustness evaluation.
- v0.3.3 — отрицательная проверка изменённой среды.
- v0.3.4 — benign redesign.
- v0.3.5 — frozen regression.
- v0.3.6 — prospective holdout с отрицательной policy.
- v0.3.7 — новый training cycle.
- v0.3.8 — class-conditional uncertainty.
- v0.3.9 — episode-first promotion.
- v0.3.10 — minimal probabilistic cycle.
- v0.3.10.1 — уточнение семантики pending.
- v0.3.11 — текущий burden-aware frozen candidate.
- v0.3.12 — frozen multi-benchmark regression.
- v0.3.12.1 — causal-order audit.
- v0.3.12.2 — corrected regression.
- v0.3.13 — независимый environmental holdout.
- v0.3.14 — component/contract audit с последующей переоценкой scope.
- v0.3.15 — controlled local passive shadow trial.
- v0.3.15.1 — corrective runtime evidence audit.
<!-- stage-history:end -->

## 19. Текущий этап v0.3.15.1

Подробности приведены в [описании этапа](docs/experiments/v0_3_15_1.md), [errata v0.3.14](docs/experiments/v0_3_14_errata.md) и итоговом агрегированном отчёте `ml/reports/v0_3_15_1/v0_3_15_1_summary.md`.

## 20. Следующий разрешённый этап

v0.3.16 заблокирован. Сначала требуется новый заранее frozen local runtime trial, который использует исправленный exporter и создаёт собственную immutable behavioral evidence без обучения и production connection.

## 21. Структура репозитория

- `collectors/shadow` — event contract и integrated passive exporter;
- `collectors/shadow_trial` — исторический trial pipeline v0.3.15;
- `ml/experiments` — frozen protocols и stage runners;
- `ml/reports` — отслеживаемые агрегированные evidence bundles отдельных этапов;
- `runtime` — локальные неотслеживаемые артефакты;
- `docs` — статус, методология и ограничения.

## 22. Локальный запуск

Корректирующий аудит запускается командой `python -m ml.experiments.v0_3_15_1.run_v0_3_15_1 --strict`. Он не использует внешнюю сеть и не выполняет model fit.

## 23. Тестирование

Основные команды: `python -m pytest ml/tests`, `python -m pytest collectors/shadow/tests`, `python -m pytest collectors/shadow_trial/tests`, `python -m pytest backend/tests`, а также compileall и validators из CI.

## 24. Reproducibility и immutable artifacts

Исторические frozen protocols, policy results и bundle manifests не переписываются. Исправления оформляются новым этапом, errata и claim-evidence ledger. Raw PCAP, predictions, events, spool, checkpoints и traces остаются вне Git.

## 25. Политика данных и privacy

События используют хэшированные идентификаторы и allowlist. Privacy audit сканирует canonical/serialized events, spool, retry journal, delivery logs, ACK, checkpoint, faults, performance и bundle reports. Raw payload, credentials, labels и feature vectors в passive telemetry запрещены.

## 26. Ограничения и roadmap

Текущие результаты лабораторные. v0.3.16 может быть рассмотрен только после положительной новой runtime evidence; ветка v0.4.x остаётся отдельным архитектурным направлением и не означает production readiness.
