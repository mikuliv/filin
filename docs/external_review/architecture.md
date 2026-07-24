# Архитектура независимой проверки

## Назначение

Архитектура разделяет данные, labels, inference, evaluation, review и approval
так, чтобы ни одна роль не могла незаметно изменить frozen result.

## Роли

- `project_owner` утверждает protocol до freeze и предоставляет candidate ID;
- `data_provider` готовит inputs, identity, provenance и manifests;
- `label_custodian` хранит labels и контролирует reveal;
- `trial_operator` выполняет frozen inference;
- `independent_evaluator` проверяет reveal и рассчитывает metrics;
- `external_reviewer` проверяет package integrity и process;
- `result_approver` фиксирует итоговый outcome.

Конфликты ролей определены только
[role matrix](../../ml/reports/v0_3_18/role_separation_matrix.json).

## Trust boundaries

1. Provider boundary отделяет source data от проекта.
2. Blind boundary отделяет operator от labels.
3. Candidate boundary фиксирует artifact и contracts read-only.
4. Evaluation boundary отделяет calculation от inference.
5. Review boundary отделяет process verification от approval.
6. Publication boundary ограничивает раскрываемые материалы.

## Namespaces данных

- `inputs` — blind PCAP и manifests;
- `labels` — отдельное хранилище custodian;
- `prediction_namespace` — submission operator;
- `evaluation` — revealed labels, frozen predictions и result;
- `review_package` — manifests, commitments и aggregate evidence;
- `reproducibility_package` — verifier и разрешённые sources;
- `runtime_only_trial_execution_package` — только для отдельно разрешённого
  execution, сейчас не используется.

## Blind sequence

```text
dataset manifest
→ label commitment
→ holdout commitment
→ candidate commitment
→ evaluator commitment
→ blind input handoff
→ frozen inference
→ prediction validation
→ prediction commitment
→ label reveal
→ reveal verification
→ frozen evaluation
→ result bundle
→ independent review
→ result approval
→ finalization
```

Перестановка reveal и prediction commitment нарушает protocol.

## Commitments

Commitment связывает canonical content с SHA-256. Он не является электронной
подписью. Canonicalization использует UTF-8 JSON, sorted keys и compact
separators; duplicate keys и non-finite numbers запрещены.

Parent commitments связывают dataset, labels, holdout, candidate, evaluator,
predictions и result. Package root commitment связывает разрешённое дерево
файлов.

## Поток материалов

Provider передаёт blind inputs operator, а labels custodian. Operator
замораживает predictions. Custodian раскрывает labels только после commitment.
Evaluator создаёт result. Reviewer проверяет весь процесс. Approver фиксирует
ровно один outcome.

## Fail-closed поведение

Missing provenance, commitment mismatch, role conflict, chronology violation,
external route, backend call, incomplete predictions и nondeterminism
останавливают процесс. Ошибка не исправляется незаметной заменой evidence.

## Отсутствие backend и production

Inference и verification изолированы от сети и backend. Passive runtime,
production connections, notifications и automatic actions не входят в
external review workflow. Reference packages не дают таких полномочий.

## Граница v0.3.18

Архитектура проверена только на synthetic rehearsal. Она подтверждает
целостность design и tools, но не external scientific validity.

## Связанные документы

- [README пакета](README.md)
- [Руководство reviewer](reviewer_guide.md)
- [Условия остановки](stop_conditions.md)
- [Воспроизводимость](reproducibility_guide.md)
- [Frozen protocol](../../ml/protocols/v0_3_18_external_review_protocol.yaml)
- [Blind workflow](../../ml/reports/v0_3_18/blind_holdout_protocol.json)
- [Текущий статус](../status/current-status.md)
