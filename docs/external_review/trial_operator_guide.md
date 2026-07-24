# Руководство trial operator

## Назначение роли

Trial operator выполняет frozen inference над blind inputs и замораживает
prediction submission. Он не видит labels до prediction commitment, не
вычисляет итоговые метрики и не утверждает результат.

## Место роли в процессе испытания

Operator работает на шагах `blind_input_handoff`, `frozen_inference`,
`prediction_validation` и `prediction_commitment`. Фактическое выполнение
external trial сейчас запрещено; руководство предназначено для review и
планирования.

## Требования к независимости

- operator получает только inputs, candidate runtime и prediction namespace;
- labels хранятся у отдельного custodian;
- actor и действия фиксируются в chronology;
- candidate, protocol и evaluator identities задаются до запуска.

## Допустимое совмещение ролей

Frozen matrix не разрешает считать молчаливое совмещение безопасным. Любое
совмещение должно быть заранее проверено и отражено в role attestations.

## Запрещённое совмещение ролей

Operator конфликтует с `label_custodian`, `independent_evaluator` и
`result_approver`. Он не получает полномочия reviewer или data provider только
из-за технического доступа к среде.

## Входные материалы

- blind PCAP inputs и dataset manifest;
- blind holdout и candidate commitments;
- evaluator commitment, если он входит в execution package;
- frozen protocol и inference instructions;
- episode manifest и ожидаемый prediction namespace;
- chronology template;
- prediction submission и commitment schemas.

## Подготовка к работе

1. Проверить dataset manifest, file count, sizes и hashes.
2. Сверить holdout ID и dataset commitment.
3. Проверить candidate commitment и запреты fit/change.
4. Сверить evaluator commitment без запуска evaluation.
5. Подготовить чистую изолированную среду.
6. Отключить внешнюю сеть, backend и production routes.
7. Смонтировать candidate и protocol read-only.
8. Убедиться, что labels недоступны.
9. Зафиксировать начало в chronology.

## Порядок действий

1. Принять blind input handoff и записать его identity.
2. Проверить вход только как supported `pcap`.
3. Запустить frozen inference без fit и calibration.
4. Не менять feature contract, thresholds или class taxonomy.
5. Сохранить prediction для каждого ожидаемого input/episode ID.
6. Сохранить frozen abstention как abstention, не заменяя классом.
7. Провести schema validation submission.
8. Проверить missing, duplicate и invalid predictions.
9. Сопоставить prediction count с manifest.
10. Canonically serialize submission.
11. Рассчитать submission SHA-256.
12. Создать prediction commitment.
13. Зафиксировать commitment в chronology.
14. Перевести submission в read-only состояние.
15. Передать commitment custodian, а frozen submission evaluator.

## Обязательные проверки

- candidate ID и artifact hash совпадают;
- `fit_allowed=false`;
- threshold, calibration и feature changes запрещены;
- сеть и backend не использовались;
- каждый prediction относится к известному holdout ID;
- duplicate и missing records не скрыты;
- abstention semantics сохранена;
- commitment создан до label reveal.

## Создаваемые артефакты

- schema-valid prediction submission;
- prediction commitment;
- operator role attestations;
- chronology events запуска, validation и freeze;
- execution log без labels и секретов;
- error record при любом отклонении.

## Передача материалов следующей роли

Label custodian получает только подтверждение prediction commitment и его
identity. Evaluator получает frozen predictions после reveal вместе с
commitments. Operator не объединяет labels и predictions самостоятельно.

## Основания для остановки

- manifest mismatch или unsupported format;
- candidate/evaluator commitment mismatch;
- labels доступны до freeze;
- обнаружена сеть, backend или automatic action;
- candidate не может быть смонтирован read-only;
- prediction set неполон или не проходит schema validation.

## Основания для признания испытания недействительным

Изменение candidate, thresholds, features или predictions после reveal;
ранний доступ к labels; commitment mismatch; post-hoc exclusions и
unauthorized retry после reveal являются основаниями invalidation.

## Работа с ошибками и расхождениями

До prediction commitment технический сбой можно расследовать без доступа к
labels. Сохраняются logs, last valid checkpoint и chronology. Ошибка не
исправляется подменой input или candidate.

После commitment submission не изменяется. Любое расхождение hash считается
критическим и передаётся reviewer/approver.

## Повторный запуск и новая ревизия

Restart до reveal допустим только если frozen identities и blind boundary
сохранены, а причина и все предыдущие попытки записаны. После reveal повтор
не может заменить исходный результат и требует новой protocol revision.

## Защита данных и конфиденциальность

Operator обрабатывает только минимальный input namespace. Labels, credentials,
private keys и неразрешённый payload не копируются в logs. Outputs передаются
по согласованному каналу с hash verification.

## Ограничения интерпретации

Успешное выполнение inference доказывает техническое завершение шага, а не
прохождение scientific gates. Missing predictions и abstentions должны
оставаться видимыми evaluator.

## Контрольный список

- [ ] manifests и commitments проверены;
- [ ] среда изолирована;
- [ ] labels недоступны;
- [ ] candidate и protocol read-only;
- [ ] fit, tuning и selection не выполнялись;
- [ ] все predictions провалидированы;
- [ ] missing/duplicate/invalid counts зафиксированы;
- [ ] abstentions сохранены;
- [ ] prediction commitment создан до reveal;
- [ ] chronology полна;
- [ ] frozen submission передан без изменений.

## Связанные документы

- [Политика приёма данных](data_acceptance_policy.md)
- [Руководство custodian](label_custodian_guide.md)
- [Руководство evaluator](evaluator_guide.md)
- [Условия остановки](stop_conditions.md)
- [Blind holdout policy](../../ml/reports/v0_3_18/blind_holdout_protocol.json)
- [Prediction schema](../../external_review/contracts/prediction_submission_v1.schema.json)
- [Текущий статус](../status/current-status.md)
