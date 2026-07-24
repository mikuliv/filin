# Руководство по воспроизводимости

## Назначение роли

Reproducibility check подтверждает, что переданный package можно проверить
без Git history, сети и backend, а frozen evaluator на идентичных inputs
создаёт идентичный canonical result.

## Место проверки в процессе

Проверка выполняется над reproducibility package до independent review или по
запросу reviewer. Она не является отдельной frozen ролью и не заменяет
external reviewer либо evaluator.

## Требования к независимости

Проверяющий не меняет package, candidate, evaluator или protocol. Environment,
команды и результаты журналируются. Проверка проводится в clean directory.

## Допустимое совмещение

Технический запуск может выполнить reviewer, если это не нарушает role matrix.
Результат всё равно трактуется как verification package, а не approval.

## Запрещённое совмещение

Нельзя использовать reproducibility run для повторного scientific evaluation
после reveal, изменения predictions или обхода разделения ролей.

## Входные материалы

- package archive или directory;
- detached package manifest hash;
- package manifest и root commitment;
- candidate, evaluator и protocol commitments;
- source allowlist;
- standalone verifier;
- canonical inputs и expected outputs;
- environment requirements.

## Подготовка к работе

1. Создать новый пустой каталог.
2. Записать platform и Python version.
3. Отключить network routes.
4. Убедиться в отсутствии backend credentials.
5. Скопировать package без изменения timestamps/content.
6. Рассчитать hash полученного container/archive.

## Порядок действий

1. Проверить detached manifest hash.
2. Разобрать manifest без duplicate JSON keys.
3. Отклонить non-finite numbers.
4. Проверить source allowlist и отсутствие unknown files.
5. Проверить path confinement и отсутствие traversal.
6. Пересчитать hash каждого файла.
7. Восстановить sorted manifest tree.
8. Сверить root commitment.
9. Проверить candidate commitment и parent identities.
10. Проверить evaluator commitment.
11. Проверить protocol/metric policy commitment.
12. Запустить standalone verifier.
13. Запустить frozen evaluator на packaged fixtures/inputs.
14. Canonically serialize output.
15. Сравнить output hash и expected result.
16. Повторить запуск в том же environment.
17. Сохранить logs и итог verification.

## Canonical serialization

Frozen rule — UTF-8 JSON с sorted keys и compact separators. Duplicate keys и
non-finite numbers запрещены. SHA-256 commitment подтверждает content
identity, но не является электронной подписью.

## Обязательные проверки

- package не требует Git history;
- network/backend calls отсутствуют;
- source allowlist полон;
- все hashes и root commitment совпадают;
- candidate/evaluator/protocol identities совпадают;
- deterministic runs дают одинаковый canonical output;
- expected outputs относятся к тому же package identity.

## Что проверяется без Git history

Проверяются manifests, commitments, schemas, chronology, verifier, evaluator
и packaged evidence. История разработки, авторство commit и полнота внешнего
dataset не выводятся из standalone package.

## Создаваемые артефакты

- verification log;
- environment metadata;
- пересчитанный root commitment;
- список checked files;
- canonical output hash;
- discrepancy report;
- итог `passed` или fail-closed result.

## Передача материалов

Reviewer получает logs, package identity, environment metadata и discrepancy
report. Исходный package передаётся неизменным; verification output не
подменяет evaluation result.

## Основания для остановки

- detached hash или root commitment mismatch;
- unknown/missing file;
- path traversal;
- unsupported schema;
- network/backend dependency;
- evaluator nondeterminism;
- expected output относится к другой identity.

## Основания invalidation

Corrupted bundle, changed commitment или попытка использовать изменённый
package как исходный result нарушают integrity. Решение об outcome принимает
approver по frozen stop policy.

## Работа с ошибками и расхождениями

Сохраняются точная команда, exit code, stderr/stdout, environment и hashes.
Mismatch не «нормализуется» ручным редактированием. Unsupported environment
отделяется от content mismatch и передаётся reviewer.

## Повторный запуск и новая ревизия

Повтор на идентичном package допустим и обязан быть детерминированным.
Изменение allowlist, source, expected output или commitment создаёт новую
revision. Старый package и его verification result сохраняются.

## Защита данных и конфиденциальность

Используется минимальный package level. Logs не должны содержать raw secrets,
credentials или лишние labels. Package удаляется по согласованной retention
policy после сохранения требуемого aggregate evidence.

## Ограничения интерпретации

Reproducibility подтверждает повторяемость и integrity, но не
репрезентативность dataset, корректность labels или научное обобщение. Успешная
synthetic rehearsal v0.3.18 имеет `scientific_evidence=false`.

## Контрольный список

- [ ] clean directory подготовлен;
- [ ] сеть и backend недоступны;
- [ ] detached hash проверен;
- [ ] source allowlist проверен;
- [ ] file hashes и root commitment совпали;
- [ ] candidate/evaluator/protocol commitments совпали;
- [ ] standalone verifier прошёл;
- [ ] canonical result совпал;
- [ ] повторный запуск идентичен;
- [ ] logs и environment metadata сохранены;
- [ ] scientific claims не расширены.

## Связанные документы

- [README пакета](README.md)
- [Руководство reviewer](reviewer_guide.md)
- [Архитектура](architecture.md)
- [Известные ограничения](known_limitations.md)
- [Frozen protocol](../../ml/protocols/v0_3_18_external_review_protocol.yaml)
- [Policy result](../../ml/reports/v0_3_18/v0_3_18_policy_result.json)
