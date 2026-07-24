# Руководство result approver

## Назначение роли

Result approver фиксирует окончательный procedural outcome на основании
result bundle, chronology и review findings. Он не пересчитывает metrics и не
исправляет evidence.

## Место роли в процессе испытания

Approver действует после `independent_review`, на шагах `result_approval` и
`finalization`. Package review v0.3.19 не является фактическим approval
внешнего trial, потому что execution пока запрещён.

## Требования к независимости

- approver не создаёт проверяемые inputs, labels, predictions или metrics;
- его actor/namespace фиксируются role attestation;
- решение опирается на frozen policies, а не желаемый outcome;
- отрицательный результат принимается и сохраняется.

## Допустимое совмещение ролей

Для реального trial frozen matrix требует отдельного actor approver.
Допустимых совмещений с остальными шестью ролями не предусмотрено.

## Запрещённое совмещение ролей

Approver конфликтует с `project_owner`, `data_provider`, `trial_operator`,
`label_custodian`, `independent_evaluator` и `external_reviewer`.

## Входные материалы

- frozen protocol и stop policy;
- dataset, holdout, candidate, evaluator, label и prediction commitments;
- role attestations и complete chronology;
- machine-readable evaluation result;
- package manifest и root commitment;
- standalone/reproducibility verifier reports;
- reviewer findings с допустимыми statuses;
- limitations, sample plan и acceptance criteria.

## Подготовка к работе

1. Подтвердить собственную независимость.
2. Получить immutable result bundle.
3. Проверить package/root commitment.
4. Убедиться, что reviewer завершил review.
5. Выделить все `blocks_approval`.
6. Сверить разрешённые outcome со stop policy.

## Порядок действий

1. Проверить completeness входных материалов.
2. Сверить все parent commitments.
3. Проверить chronology blind sequence.
4. Проверить role separation.
5. Проверить verifier и determinism evidence.
6. Сверить evaluator result с summary.
7. Рассмотреть каждый reviewer finding.
8. Отделить process validity от scientific outcome.
9. Выбрать ровно один frozen outcome.
10. Записать rationale и supporting evidence.
11. Перечислить limitations и сохраняющиеся запреты.
12. Зафиксировать необходимость новой revision, если применимо.
13. Canonically сохранить approval decision.
14. Завершить chronology и finalization.

## Допустимые итоговые статусы

### `trial_stopped`

Процесс прекращён до валидного завершения, например из-за privacy finding,
unsupported input или невозможности продолжить безопасно. Допустимо сохранить
evidence, устранить организационную причину и планировать новую revision.
Запрещено заявлять scientific pass или failure.

### `trial_invalidated`

Blind или frozen integrity нарушена: early reveal, commitment mismatch,
changed identity, overlap, role/chronology violation либо unauthorized retry.
Следующее действие — сохранить invalidated result и при отдельном разрешении
создать новую revision. Запрещено использовать metrics как валидное
подтверждение candidate.

### `trial_failed_scientifically`

Процедура валидна, но заранее согласованные scientific criteria не пройдены.
Negative result сохраняется; возможна новая candidate lineage и новое
испытание. Запрещено переписывать thresholds или исключать samples post hoc.

### `trial_failed_operationally`

Научный вывод невозможен из-за operational failure: incomplete predictions,
unsupported environment, nondeterminism или неустранимый execution failure.
Допустима отдельная новая revision после анализа причины. Запрещено объявлять
scientific failure или pass без валидного evaluation.

### `trial_completed_passed`

Валидная процедура завершена и заранее согласованные gates пройдены. Это
разрешает только выводы, предусмотренные trial plan; backend, shadow mode и
production не разрешаются автоматически.

### `trial_completed_failed`

Валидный trial завершён с общим отрицательным итогом, который не следует
подменять остановкой или invalidation. Допустимы сохранение результата и
планирование новой revision. Запрещено удалять отрицательное evidence.

## Обязательные проверки

- все commitments согласованы;
- chronology не содержит раннего reveal;
- role conflicts отсутствуют;
- result deterministically reproduced;
- findings `blocks_approval` разрешены либо outcome отражает блокировку;
- summary не противоречит machine-readable result;
- outcome принадлежит frozen списку;
- limitations включены в decision.

## Создаваемые артефакты

Approval decision содержит package identity, выбранный outcome, rationale,
commitment references, findings disposition, limitations, next-action
boundary, actor attestation и timestamp.

## Передача материалов

Finalization package включает исходный result bundle, findings и approval
decision. Ничто не заменяет исходные negative или invalidated artifacts.

## Основания для остановки

- неполный result bundle;
- unresolved commitment mismatch;
- отсутствующий reviewer report;
- неразрешённый `blocks_approval`;
- роль approver конфликтует;
- summary скрывает machine-readable outcome.

## Основания для признания испытания недействительным

Approver применяет frozen stop conditions, не создавая новые. Invalidation
отличается от scientific/operational failure нарушением допустимости процесса.

## Работа с ошибками и расхождениями

При расхождении summary и machine-readable result решение не принимается до
оформления finding. Approver не редактирует evaluator output. Ошибочная
разметка, prediction или commitment после freeze требует новой revision.

## Повторный запуск и новая ревизия

Новая revision имеет новые identities и полный blind workflow. Она не
перезаписывает прежнее approval decision. Повтор approval над идентичным
bundle допустим только как verification и должен дать тот же outcome.

## Защита данных и конфиденциальность

Approver использует aggregate result и review materials. Доступ к raw inputs
или labels не требуется по умолчанию. Decision не раскрывает confidential
identifiers сверх согласованного publication scope.

## Ограничения интерпретации

Даже `trial_completed_passed` не означает production readiness. Текущий
проект разрешает только v0.3.19 package review; external trial execution,
backend integration и production остаются запрещены.

## Контрольный список

- [ ] независимость approver подтверждена;
- [ ] полный bundle получен;
- [ ] commitments и chronology проверены;
- [ ] role separation подтверждено;
- [ ] evaluator result и findings рассмотрены;
- [ ] все blocks_approval обработаны;
- [ ] выбран ровно один допустимый outcome;
- [ ] negative result сохранён;
- [ ] limitations и запреты записаны;
- [ ] approval decision и finalization завершены.

## Связанные документы

- [Руководство reviewer](reviewer_guide.md)
- [Руководство evaluator](evaluator_guide.md)
- [Условия остановки](stop_conditions.md)
- [Известные ограничения](known_limitations.md)
- [Stop policy JSON](../../ml/reports/v0_3_18/stop_conditions.json)
- [Role matrix](../../ml/reports/v0_3_18/role_separation_matrix.json)
- [Текущий статус](../status/current-status.md)
