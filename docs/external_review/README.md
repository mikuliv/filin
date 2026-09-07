# Пакет независимой проверки

## Статус и назначение

Каталог объясняет frozen external review package v0.3.18. Этап завершён как
`completed / passed`, но только для synthetic protocol rehearsal:
`scientific_evidence=false`. Реальные данные, организация и модель в
репетиции не использовались.

Следующий допустимый этап v0.3.19 ограничен независимым package review и
согласованием trial plan. External trial execution, real organization trial,
real traffic capture, shadow mode, backend integration, production, real
notifications, automatic enforcement и network blocking запрещены.

## Кому предназначен пакет

- reviewer проверяет integrity, roles, chronology и limitations;
- trial planner использует policies и checklists, не запуская trial;
- data provider планирует identity, provenance и безопасную передачу;
- label custodian планирует blind label workflow;
- operator изучает frozen inference и prediction freeze;
- evaluator изучает deterministic metrics;
- approver изучает допустимые outcomes и finalization;
- юрист проверяет применимость требований вне этого технического пакета.

## Рекомендуемый порядок чтения

1. [Подтверждённая область](confirmed_scope.md).
2. [Известные ограничения](known_limitations.md).
3. [Архитектура процесса](architecture.md).
4. [Руководство reviewer](reviewer_guide.md).
5. [Ролевое руководство конкретного участника](#ролевые-руководства).
6. [Приём данных](data_acceptance_policy.md),
   [метрики](metric_policy.md) и [stop conditions](stop_conditions.md).
7. [Воспроизводимость](reproducibility_guide.md).
8. [Правовые, transfer, retention и publication checklists](#policies-и-checklists).

## Что передавать на первом контакте

- этот README;
- confirmed scope и known limitations;
- текущий status;
- architecture;
- reviewer guide;
- readiness decision;
- предупреждение о запрете фактического trial.

Первый контакт не должен включать raw PCAP, labels, credentials, candidate
artifact или runtime-only execution package.

## Что передавать для технического review

- frozen protocol;
- review overview и reproducibility package;
- package manifest, detached hash и root commitment;
- candidate/evaluator/protocol commitments;
- role matrix, chronology и aggregate result;
- standalone verifier;
- machine-readable policies и schemas;
- limitations и reviewer finding template.

Package level выбирается по минимально необходимому доступу.

## Что используется только при планировании trial

- data provider, custodian, operator, evaluator и approver guides;
- sample sufficiency и data acceptance policies;
- legal, transfer, retention и publication checklists;
- runtime-only trial execution package.

Наличие этих материалов не является разрешением выполнить trial.

## Ролевые руководства

- [Data provider](data_provider_guide.md)
- [Label custodian](label_custodian_guide.md)
- [Trial operator](trial_operator_guide.md)
- [Independent evaluator](evaluator_guide.md)
- [External reviewer](reviewer_guide.md)
- [Result approver](result_approver_guide.md)

Project owner ограничен frozen protocol: он утверждает protocol до freeze и
предоставляет candidate identity, но не выполняет approval.

## Policies и checklists

- [Data acceptance](data_acceptance_policy.md)
- [Metric policy](metric_policy.md)
- [Stop conditions](stop_conditions.md)
- [Legal checklist](legal_requirements_checklist.md)
- [Data transfer](data_transfer_requirements.md)
- [Retention and deletion](retention_and_deletion_requirements.md)
- [Publication](publication_requirements.md)

Human-readable документы объясняют применение. Авторитетные значения находятся
в linked machine-readable policies; документация не меняет frozen rules.

## Проверка пакета

Начните с [reproducibility guide](reproducibility_guide.md). Standalone
verifier работает в clean directory без Git, сети и backend. Успешная проверка
целостности не является scientific validation.

## Связанные документы

- [Общий индекс](../index.md)
- [Текущий статус](../status/current-status.md)
- [Запрещённые возможности](../status/prohibited-capabilities.md)
- [Контракты](../contracts/index.md)
- [Frozen protocol](../../ml/protocols/v0_3_18_external_review_protocol.yaml)
- [Readiness decision](../../ml/reports/v0_3_18/readiness_decision.json)
