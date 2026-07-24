# Практическое применение stop и invalidation conditions

## Авторитетный источник

Полный frozen список находится в
[stop conditions JSON](../../ml/reports/v0_3_18/stop_conditions.json).

## Когда остановить процесс

Работа немедленно переводится в fail-closed состояние при:

- раннем label reveal;
- изменении candidate, evaluator, threshold или contracts;
- detected overlap или changed dataset manifest;
- commitment mismatch;
- missing provenance или unsupported format;
- privacy, credential или prohibited payload finding;
- external route, backend call или automatic action;
- corrupted bundle;
- role conflict или chronology violation;
- insufficient sample plan;
- unverifiable origin;
- evaluator nondeterminism;
- incomplete prediction set;
- post-hoc exclusions;
- unauthorized retry после reveal.

## Stop и invalidation

`trial_stopped` означает прекращение до валидного завершения.
`trial_invalidated` означает нарушение blind/frozen integrity. Scientific и
operational failures применимы только в соответствии с фактическим состоянием
процесса; они не заменяют invalidation.

## Практический порядок

1. Прекратить дальнейшие изменения artifacts.
2. Сохранить logs, chronology и hashes.
3. Зафиксировать condition и время.
4. Ограничить дальнейший доступ.
5. Передать evidence reviewer и approver.
6. Выбрать outcome только из frozen списка.
7. Сохранить negative result.

## Ошибки и новая revision

Нельзя «доделать» исходный trial после reveal. Replacement attempt требует
новой revision, новых identities и полного blind workflow. Прежний outcome
остаётся доступным.

## Связанные документы

- [Руководство approver](result_approver_guide.md)
- [Руководство reviewer](reviewer_guide.md)
- [Архитектура](architecture.md)
- [Blind protocol](../../ml/reports/v0_3_18/blind_holdout_protocol.json)
- [Текущий статус](../status/current-status.md)
