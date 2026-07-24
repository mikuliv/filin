# Подтверждённая область external review package

## Подтверждённые возможности

v0.3.18 подтвердил на synthetic fixtures:

- frozen protocol до workflow implementation;
- 13 JSON Schema contracts;
- canonical SHA-256 commitments;
- role separation и chronology validation;
- blind prediction-before-reveal sequence;
- deterministic evaluator;
- package builder и standalone verifier;
- source allowlist и root commitment;
- synthetic rehearsal;
- отклонение 40 из 40 negative scenarios;
- privacy, secret и artifact exclusion gates.

## Supporting evidence

- [Policy result](../../ml/reports/v0_3_18/v0_3_18_policy_result.json)
- [Bundle manifest](../../ml/reports/v0_3_18/v0_3_18_bundle_manifest.yaml)
- [Frozen protocol](../../ml/protocols/v0_3_18_external_review_protocol.yaml)
- [Role matrix](../../ml/reports/v0_3_18/role_separation_matrix.json)
- [Blind workflow](../../ml/reports/v0_3_18/blind_holdout_protocol.json)
- [Metric policy](../../ml/reports/v0_3_18/metric_policy.json)
- [Stop policy](../../ml/reports/v0_3_18/stop_conditions.json)

## Что означает passed

`completed / passed` означает, что design, contracts, tooling и synthetic
rehearsal прошли gates v0.3.18. Это разрешило только
`candidate_ready_for_v0_3_19_external_package_review=true`.

## Что не означает passed

Passed не подтверждает:

- качество на реальных внешних данных;
- участие независимой организации;
- завершение external validation;
- готовность реального trial;
- shadow mode, backend integration или production;
- реальные notifications или enforcement.

## Разрешённая следующая работа

v0.3.19 может выполнить package review и согласовать trial plan, roles,
sample plan, legal basis и acceptance criteria. Само execution требует
отдельного решения после review.

## Ограничения evidence

Rehearsal использовала deterministic predictor вместо реальной модели и
synthetic data вместо внешнего holdout. Поэтому
`synthetic_rehearsal_scientific_evidence=false`.

## Граница claims

Любой claim должен указывать stage, usage mode, dataset scope и limitations.
Package integrity нельзя описывать как model accuracy, а reproducibility —
как representativeness.

## Связанные документы

- [Известные ограничения](known_limitations.md)
- [Текущий статус](../status/current-status.md)
- [Подтверждённые возможности проекта](../status/confirmed-capabilities.md)
- [Readiness decision](../../ml/reports/v0_3_18/readiness_decision.json)
- [README пакета](README.md)
