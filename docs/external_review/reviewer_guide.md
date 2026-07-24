# Руководство внешнего reviewer

## Назначение роли

External reviewer — независимый проверяющий пакета. Он подтверждает
целостность manifests, commitments, chronology и разделение ролей, но не
вычисляет метрики и не утверждает итог испытания.

Reviewer отличается от evaluator: evaluator рассчитывает frozen metrics, а
reviewer проверяет процесс и evidence. Reviewer отличается от result approver:
approver принимает итоговое решение с учётом findings.

## Место роли в процессе испытания

Reviewer получает result bundle после frozen evaluation. Его работа находится
между шагами `result_bundle` и `result_approval`. До фактического trial
допустим только package review v0.3.19 и согласование trial plan.

## Требования к независимости

- actor и namespace фиксируются role attestation;
- reviewer не создаёт проверяемые predictions, labels или metrics;
- reviewer не должен зависеть от желаемого результата;
- все конфликты ролей раскрываются до начала review.

## Допустимое совмещение ролей

Frozen matrix не задаёт reviewer дополнительных совмещений. Любое предполагаемое
совмещение сначала проверяется по machine-readable role matrix и фиксируется
как ограничение; молчаливое совмещение недопустимо.

## Запрещённое совмещение ролей

Reviewer конфликтует с `project_owner`, `trial_operator` и `result_approver`.
Он не подменяет `independent_evaluator`, даже если способен повторить
техническую проверку результата.

## Входные материалы

- frozen protocol и protocol commitment;
- package manifest, detached hash и root commitment;
- candidate и evaluator commitments;
- dataset, provenance, holdout, label и prediction commitments;
- role attestations и chronology;
- machine-readable evaluation result;
- human-readable summary и limitations;
- отчёты standalone verifier и reproducibility check.

## Подготовка к работе

1. Получить пакет через согласованный канал без изменения файлов.
2. Создать чистый каталог без Git history, сети и backend.
3. Зафиксировать hash полученного архива или дерева.
4. Проверить полноту source allowlist.
5. Сопоставить package level с целью review.

## Порядок действий

1. Проверить detached hash package manifest.
2. Запустить standalone verifier.
3. Сверить root commitment с manifest tree.
4. Сверить candidate identity и все parent commitments.
5. Убедиться, что protocol был frozen до workflow.
6. Сверить evaluator source, metric policy и output schema.
7. Проверить dataset identity, provenance и usage mode.
8. Проверить role attestations и конфликты.
9. Восстановить chronology по canonical events.
10. Убедиться, что prediction commitment предшествует label reveal.
11. Проверить отсутствие post-hoc prediction, threshold и protocol changes.
12. Сверить evaluation result с commitments.
13. Проверить, что summary не расширяет machine-readable result.
14. Проверить limitations и unresolved acceptance thresholds.
15. Оформить findings и передать approver.

## Обязательные проверки

- все hashes имеют ожидаемый объект проверки;
- duplicate JSON keys и non-finite numbers отсутствуют;
- canonical serialization соответствует frozen protocol;
- usage mode единственный и согласованный;
- real trial не выдан за synthetic rehearsal;
- missing, duplicate и invalid predictions отражены;
- отрицательный результат не удалён и не переименован;
- claims ограничены dataset scope и coverage.

## Классификация замечаний

Допустимые статусы finding:

- `accepted` — факт подтверждён evidence;
- `accepted_with_limitation` — факт подтверждён только в указанной границе;
- `rejected_with_rationale` — claim отклонён с проверяемым обоснованием;
- `requires_new_revision` — исправление меняет frozen материал;
- `blocks_approval` — approval невозможен до разрешения нарушения.

Критичность описывается влиянием: информационное замечание, ограничение
интерпретации, требование новой revision или блокирующее нарушение.
Новые числовые уровни критичности не вводятся.

## Создаваемые артефакты

Review findings содержат ID, статус, проверенный claim, evidence reference,
наблюдение, влияние, rationale и требуемое действие. Отдельно фиксируются
версия пакета, root commitment, время review и role attestation reviewer.

## Передача материалов следующей роли

Approver получает неизменённый result bundle, review findings и список
неразрешённых блокирующих замечаний. Reviewer не передаёт «исправленную»
копию evidence вместо исходной.

## Основания для остановки

- package manifest или root commitment не сходится;
- отсутствует обязательный commitment;
- обнаружен role conflict или chronology violation;
- reveal произошёл до prediction commitment;
- verifier требует сеть или backend;
- human-readable summary скрывает отрицательный результат.

## Основания для признания испытания недействительным

Commitment mismatch, изменение frozen identity, ранний reveal, post-hoc
исключение samples, несанкционированный retry после reveal и подтверждённый
overlap относятся к основаниям invalidation по frozen stop policy.

## Работа с ошибками и расхождениями

При расхождении summary и machine-readable result авторитетен проверяемый
machine-readable artifact. Расхождение оформляется finding; reviewer не
редактирует ни один из двух файлов. Ошибка verifier сохраняется вместе с
логом, environment metadata и входным root commitment.

## Повторный запуск и новая ревизия

Повтор verifier на идентичном пакете допустим для проверки детерминизма.
Изменение package content, protocol, evaluator или commitments требует новой
revision. Новая revision не заменяет отрицательный исход прежней.

## Защита данных и конфиденциальность

Reviewer использует минимально необходимый package level. Raw PCAP, labels и
идентификаторы организации не включаются в review overview без отдельного
основания. Credentials и private keys недопустимы.

## Ограничения интерпретации

Успешный package review подтверждает процесс и целостность, но не научную
валидность модели на внешних данных. v0.3.18 — synthetic rehearsal с
`scientific_evidence=false`.

## Контрольный список

- [ ] package hash и root commitment проверены;
- [ ] source allowlist и manifests проверены;
- [ ] candidate, evaluator и protocol commitments совпали;
- [ ] roles и chronology проверены;
- [ ] post-hoc changes отсутствуют;
- [ ] result и summary согласованы;
- [ ] limitations сохранены;
- [ ] каждому finding назначен допустимый статус;
- [ ] `blocks_approval` явно перечислены;
- [ ] исходное evidence не изменено;
- [ ] материалы переданы approver.

## Связанные документы

- [Архитектура процесса](architecture.md)
- [Условия остановки](stop_conditions.md)
- [Руководство approver](result_approver_guide.md)
- [Воспроизводимость](reproducibility_guide.md)
- [Текущий статус](../status/current-status.md)
- [Frozen protocol](../../ml/protocols/v0_3_18_external_review_protocol.yaml)
- [Role matrix](../../ml/reports/v0_3_18/role_separation_matrix.json)
