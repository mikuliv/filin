# Текущие возможности

Авторитетный источник статуса — [`research-state.yaml`](research-state.yaml).

Последний завершённый исследовательский этап — v0.3.9. Его frozen policy
внутренней валидации не пройдена. Backend integration, shadow mode и production
deployment не разрешены.

## Реализовано и проверяется

- изолированный Docker-стенд с внутренним allowlist;
- per-execution capture с DNS для будущего internal-only smoke;
- copy-aware marker intervals с независимым control evidence;
- offline Zeek normalization и sensor aggregation;
- единый исполняемый контракт `network_sensor_v0_6_integrity`;
- application controller, удерживающий сетевое условие весь сценарий и
  откатывающий его также при ошибке или timeout;
- fail-closed predict-only guard для будущих frozen candidates;
- runtime workflows HTTP, DNS, TCP и WebSocket с machine-readable аудитом;
- типизированные SHA-256 evidence и fail-closed secure-artifact verifier.

Реализованы Mondrian conformal prediction, class-conditional kNN support и
episode evidence. Полный цикл v0.3.9 выполнен; его validation data не допускаются
к fit, calibration, выбору thresholds или повторному predict.

## Исторические результаты

v0.3.1–v0.3.9 остаются неизменяемыми записями исполнения соответствующего кода.
Новые validators, marker rules, feature formulas и runtime workflows не
применялись задним числом. Ограничения формул и доказательств перечислены в
[`limitations.md`](limitations.md) и post-v0.3.7 аудите.

## Не реализовано и не разрешено

- production capture и production validation;
- backend ML integration и online inference;
- shadow mode, active response и автоматическое блокирование;
- подтверждённые MITRE ATT&CK, Sigma, SIEM и analyst-interface pipelines;
- использование secure frozen candidate без успешной внешней проверки.

Все результаты относятся к контролируемому лабораторному стенду и не
подтверждают пригодность к эксплуатации в производственной инфраструктуре.
