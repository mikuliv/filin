# Известные ограничения external review package

## Отсутствие внешней validation

Независимый reviewer ещё не проверял пакет, real blind holdout не проводился,
а external validation не завершена. На внешних данных не рассчитана ни одна
научная метрика.

## Synthetic rehearsal

v0.3.18 использовал synthetic fixtures и deterministic predictor, а не
реальную модель и организационный dataset. Результат имеет
`scientific_evidence=false`.

## Ограничения данных

- поддержан только PCAP;
- representativeness не доказана;
- универсальный sample minimum не установлен;
- organization/environment context не согласован;
- непроверяемый overlap требует limitation и provider attestation;
- качество labels зависит от внешней provenance.

## Closed-set ограничения

Frozen taxonomy содержит `benign`, `auth_failures`, `beacon`, `low_rate_dos`,
`port_scan` и `web_probe`. Unsupported classes требуют согласованного handling
до commitment. Closed-set metrics не доказывают поведение на неизвестных
классах.

## Ограничения evaluator

Evaluator детерминированно рассчитывает frozen metrics, но policy complete
только для protocol rehearsal. Organization-specific false-positive,
false-negative и minimum macro-F1 thresholds не согласованы.

## Ограничения claims

Нельзя заявлять production readiness, operational effectiveness в реальной
организации, SIEM/backend compatibility или automatic protection. Package
verifier проверяет integrity и process, а не scientific generalization.

## Правовые ограничения

Технические checklists не являются договором или юридическим заключением.
Передача реальных данных требует проверки компетентным юристом применимой
юрисдикции.

## Сохраняющиеся запреты

External trial execution, real organization trial, real traffic capture,
shadow mode, backend integration, production, real notifications, automatic
enforcement и network blocking запрещены.

## Как отражать ограничения

Limitations включаются в review findings, evaluation summary, approval
decision и publication. Неизвестность не заменяется положительным
предположением.

## Связанные документы

- [Подтверждённая область](confirmed_scope.md)
- [Metric policy](metric_policy.md)
- [Data acceptance](data_acceptance_policy.md)
- [Publication requirements](publication_requirements.md)
- [Текущий статус](../status/current-status.md)
- [Frozen metric policy](../../ml/reports/v0_3_18/metric_policy.json)
