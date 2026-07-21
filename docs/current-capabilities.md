# Текущие подтверждённые возможности

Источник статуса: [`status/project-status.yaml`](status/project-status.yaml).

## Проверено

- frozen candidate v0.3.11 и неизменная 51-feature schema;
- independent environmental holdout v0.3.13;
- controlled local trial v0.3.15 с неизменным scientific bundle;
- hash-integrity всех доступных файлов bundle v0.3.15;
- corrected integrated at-least-once exporter v0.3.15.1;
- строгий ACK contract, retry classification и drop reconciliation;
- hash-verified resume с detached manifest lock и path confinement;
- реальные worker/batch profiles с resource sampling во время нагрузки;
- behavioral fault, crash, privacy, resume и topology tests.

## Переоценённый scope

v0.3.14 подтверждает event contract и отдельные компоненты, но не доказывает full integrated fault readiness. Подробности: [errata v0.3.14](experiments/v0_3_14_errata.md).

Оригинальный v0.3.15 result сохранён, однако его точные runtime claims о fault injection, retry и recovery не прошли повторную behavioral атрибуцию к исходному execution path. Подробности: [аудит v0.3.15.1](experiments/v0_3_15_1.md).

## Не разрешено

Production, backend integration, shadow mode, automatic enforcement и внешние сетевые получатели запрещены. v0.3.16 заблокирован до нового evidence-bearing runtime trial.
