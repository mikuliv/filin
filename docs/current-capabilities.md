# Текущие подтверждённые возможности

Источник статуса: [`status/project-status.yaml`](status/project-status.yaml).

## Проверено

- development candidate v0.3.15.4, исторический frozen candidate v0.3.11 и versioned 51-feature schema v2;
- independent environmental holdout v0.3.13;
- controlled local trial v0.3.15 с неизменным scientific bundle;
- hash-integrity всех доступных файлов bundle v0.3.15;
- corrected integrated at-least-once exporter v0.3.15.1;
- prospective local runtime evidence v0.3.15.2: 2 490/2 490 reconciled events и 35/35 fault-oracles;
- полный evidence-linked regression analysis v0.3.15.3 для 120/120 эпизодов;
- additive exact-latency, normalized-CPU и synthetic raw-ACK evidence contracts для будущего trial;
- строгий ACK contract, retry classification и drop reconciliation;
- hash-verified resume с detached manifest lock и path confinement;
- реальные worker/batch profiles с resource sampling во время нагрузки;
- behavioral fault, crash, privacy, resume и topology tests.

## Переоценённый scope

v0.3.14 подтверждает event contract и отдельные компоненты, но не доказывает full integrated fault readiness. Подробности: [errata v0.3.14](experiments/v0_3_14_errata.md).

Оригинальный v0.3.15 result сохранён, однако его точные runtime claims о fault injection, retry и recovery не прошли повторную behavioral атрибуцию к исходному execution path. Подробности: [аудит v0.3.15.1](experiments/v0_3_15_1.md).

v0.3.15.2 не разрешает staging connector: frozen candidate не прошёл scientific gates, а performance/privacy evidence имеет перечисленные в [отчёте](experiments/v0_3_15_2.md) ограничения.

v0.3.15.4 исправил подтверждённые scenario/feature defects и разрешил training necessity созданием нового development candidate. Результат ограничен internal audit; независимый prospective holdout v0.3.15.5 ещё не выполнен.

## Не разрешено

Production, backend integration, shadow mode, automatic enforcement и внешние сетевые получатели запрещены. v0.3.16 заблокирован до нового evidence-bearing runtime trial.
