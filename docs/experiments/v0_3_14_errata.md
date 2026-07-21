# Errata v0.3.14

Исходные артефакты v0.3.14 не изменялись. Корректирующий аудит v0.3.15.1 установил, что формулировка о полном прохождении fault campaign была шире фактической проверки.

## Подтверждённый объём

На v0.3.14 были реализованы и проверены `shadow_event_v1`, schema/privacy validation, deterministic identity, hash chain, bounded queue, отдельные spool/checkpoint компоненты и local mock sink. Поэтому `passive_event_contract_and_component_audit_passed=true` остаётся обоснованным.

## Неподтверждённый объём

Fault runner использовал fallback неизвестного сценария в healthy и присваивал каждому результату `passed=true`. Spool проверялся отдельно от exporter, ACK не имел строгого контракта, performance profiles не меняли фактическую topology, а resume не проверял все hashes и sizes. Поэтому `full_integrated_fault_readiness_proven_at_v0_3_14=false`.

## Последствия

Errata не отменяет independent holdout v0.3.13 и не переписывает policy JSON v0.3.14. Исправленный runtime создан только в [v0.3.15.1](v0_3_15_1.md).
