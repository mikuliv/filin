# Руководство label custodian

## Назначение роли

Label custodian независимо хранит labels, создаёт их commitment и выполняет
reveal только после валидного prediction commitment.

## Место роли в процессе испытания

Custodian участвует в `label_commitment`, затем ожидает
`prediction_commitment`, выполняет `label_reveal` и передаёт reveal package
для verification и frozen evaluation.

## Требования к независимости

- labels физически и логически отделены от operator;
- доступ к labels выдаётся по минимальной необходимости;
- actor, namespace и reveal time фиксируются;
- custodian не рассчитывает metrics и не утверждает результат.

## Допустимое совмещение ролей

Frozen matrix не задаёт безопасного совмещения custodian с операционными
ролями. Любое исключение требует отдельной проверки и не может быть
подразумеваемым.

## Запрещённое совмещение ролей

Custodian конфликтует с `trial_operator`, `independent_evaluator` и
`result_approver`. Project owner также конфликтует с custodian по frozen
matrix.

## Входные материалы

- labels и label provenance;
- holdout ID и class taxonomy;
- label manifest commitment;
- label commitment и reveal schemas;
- chronology;
- подтверждённый prediction commitment перед reveal.

## Подготовка к работе

1. Проверить holdout ID и dataset identity.
2. Сверить taxonomy с frozen metric policy.
3. Проверить label count и episode mapping.
4. Зафиксировать provenance и creation method.
5. Ограничить доступ operator и evaluator до разрешённого шага.
6. Подготовить canonical serialization.

## Порядок действий

1. Провалидировать labels и их mapping.
2. Canonically serialize labels.
3. Рассчитать `labels_sha256`.
4. Создать label commitment до blind handoff.
5. Записать commitment event в chronology.
6. Хранить labels в отдельном namespace.
7. Получить prediction commitment.
8. Проверить schema, holdout ID, count и hash reference.
9. Убедиться, что prediction commitment уже зафиксирован.
10. Создать label reveal package.
11. Связать reveal с label и prediction commitments.
12. Зафиксировать `revealed_at_ns`.
13. Передать reveal evaluator.
14. Сохранить audit trail доступа.

## Обязательные проверки

- class taxonomy неизменна;
- label provenance полна;
- canonical serialization детерминирована;
- label commitment создан до reveal;
- prediction commitment создан до reveal;
- reveal hash совпадает с первоначальным commitment;
- labels не изменялись молча;
- chronology сохраняет фактический порядок.

## Создаваемые артефакты

- label commitment;
- label reveal package;
- custodian role attestations;
- chronology events commitment/reveal;
- access audit;
- discrepancy record при mismatch.

## Передача материалов следующей роли

Evaluator получает reveal package, label commitment и prediction commitment.
Reviewer получает только необходимые commitments, chronology и aggregate
evidence согласно package level.

## Основания для остановки

- нет валидного prediction commitment;
- taxonomy или holdout ID не совпадают;
- label count/mapping неполны;
- provenance отсутствует;
- обнаружен несанкционированный доступ;
- canonical hash не воспроизводится.

## Основания для признания испытания недействительным

Early label reveal, label commitment mismatch, скрытая коррекция labels и
совмещение конфликтующих ролей являются основаниями остановки или invalidation
по frozen policy.

## Работа с ошибками и расхождениями

Исправление разметки до commitment создаёт документированную новую версию.
После commitment ошибка не устраняется заменой labels. Оформляется discrepancy,
текущий trial сохраняет исходный outcome, а исправление требует новой revision.

## Повторный запуск и новая ревизия

Повторная verification неизменного reveal допустима. Новый label set,
taxonomy, mapping или commitment означает новую revision. После reveal
unauthorized retry не заменяет исходную оценку.

## Защита данных и конфиденциальность

Labels могут раскрывать свойства environment и организации. Custodian хранит
минимальный набор, ограничивает export, не включает raw labels в Git и
соблюдает согласованные retention/deletion requirements.

## Ограничения интерпретации

Совпадение commitment подтверждает неизменность labels, но не доказывает
правильность разметки. Качество provenance и annotation process остаётся
частью limitations.

## Контрольный список

- [ ] holdout ID и taxonomy проверены;
- [ ] provenance и mapping полны;
- [ ] labels canonicalized;
- [ ] label commitment создан;
- [ ] доступ operator исключён;
- [ ] prediction commitment проверен до reveal;
- [ ] reveal совпал с label commitment;
- [ ] chronology и audit trail сохранены;
- [ ] ошибки не исправлялись молча;
- [ ] материалы переданы evaluator.

## Связанные документы

- [Руководство operator](trial_operator_guide.md)
- [Руководство evaluator](evaluator_guide.md)
- [Условия остановки](stop_conditions.md)
- [Blind protocol JSON](../../ml/reports/v0_3_18/blind_holdout_protocol.json)
- [Label commitment schema](../../external_review/contracts/label_commitment_v1.schema.json)
- [Label reveal schema](../../external_review/contracts/label_reveal_v1.schema.json)
- [Role matrix](../../ml/reports/v0_3_18/role_separation_matrix.json)
