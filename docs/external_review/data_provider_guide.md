# Руководство data provider

## Назначение роли

Data provider готовит внешний dataset, его identity, provenance и manifests.
Он подтверждает происхождение и права использования, но не запускает
inference, не рассчитывает metrics и не утверждает результат.

## Место роли в процессе испытания

Provider действует до `dataset_manifest`, `label_commitment` и
`holdout_commitment`. Фактическая передача внешних данных пока запрещена;
документ используется для package review и trial-plan agreement.

## Требования к независимости

Provider должен отделить holdout от development, training, calibration,
conformal и threshold-selection sets. Filename или случайное разделение
feature rows не доказывают независимость.

## Допустимое совмещение ролей

Любое предполагаемое совмещение проверяется до работы и фиксируется role
attestation. Наличие данных не даёт provider полномочий custodian.

## Запрещённое совмещение ролей

Provider конфликтует с `trial_operator`, `independent_evaluator` и
`result_approver`. Labels передаются отдельному label custodian.

## Входные материалы

- исходные captures и сведения об их происхождении;
- frozen data acceptance и contamination policies;
- class taxonomy;
- identity, provenance и holdout schemas;
- согласованный sample plan;
- технические legal, transfer, retention и publication checklists.

## Поддерживаемый формат

Поддержан только `pcap`. `netflow`, `csv_features` и `raw_event_rows` требуют
отдельной реализации и не принимаются текущим pipeline.

## Подготовка к работе

1. Выбрать один usage mode.
2. Подтвердить право и цель обработки.
3. Назначить псевдонимы environment и organization.
4. Отделить inputs от labels.
5. Провести privacy, credential, payload и malware checks.
6. Согласовать retention, deletion и publication restrictions.
7. Убедиться, что sample plan одобрен до holdout commitment.

## Порядок действий

1. Сформировать file manifest с paths, sizes и SHA-256.
2. Создать dataset identity.
3. Описать capture period и capture origin.
4. Зафиксировать grouping по episode и time range.
5. Зафиксировать network node, environment и organization grouping.
6. Описать label provenance и creation method.
7. Создать episode manifest commitment.
8. Создать label manifest commitment без раскрытия labels operator.
9. Провести exact file hash overlap check.
10. Провести normalized capture и session checks.
11. Проверить time, node и organization overlap.
12. Проверить scenario seed, template и duplicated label source.
13. Оформить overlap attestation для непроверяемых сравнений.
14. Зафиксировать anonymization и payload handling.
15. Передать blind PCAP operator, labels — custodian.

## Обязательные проверки

- dataset ID стабилен;
- PCAP parseable, timestamps присутствуют;
- episode manifest непуст;
- capture origin стабилен;
- taxonomy mapped до commitment;
- usage mode единственный;
- row random split не используется как доказательство;
- file manifest hash воспроизводим;
- credentials и prohibited payload отсутствуют;
- персональные данные имеют разрешённый режим обработки.

## Персональные и конфиденциальные сведения

IP, payload и organization metadata могут быть чувствительными. Provider
документирует минимизацию и anonymization. Credentials, private keys и
неразрешённые secrets являются основанием отклонения, а не материалом для
«очистки после передачи».

Checklist не заменяет проверку компетентным юристом применимой юрисдикции.

## Создаваемые артефакты

- dataset identity и provenance;
- file и episode manifests;
- dataset и holdout commitments;
- privacy и overlap attestations;
- sample-plan evidence;
- transfer/retention metadata;
- role attestations provider.

## Передача материалов следующей роли

Operator получает только blind inputs и manifests. Custodian получает labels,
label provenance и label manifest. Hashes проверяются при передаче. Namespaces
inputs и labels не объединяются.

## Основания для остановки

- unsupported format или unparseable PCAP;
- missing provenance или unclear usage right;
- credential, privacy, malware или prohibited payload finding;
- manifest mismatch;
- detected overlap;
- неподтверждённый sample plan;
- невозможность отделить labels.

## Основания для признания испытания недействительным

Изменение dataset manifest после holdout commitment, подтверждённый overlap,
ложная provenance attestation или скрытое раскрытие labels нарушают frozen
protocol и могут invalidates trial.

## Работа с ошибками и расхождениями

Ошибочный manifest не редактируется незаметно. До commitment создаётся новая
версия с документированной причиной. После commitment требуется новая
revision; прежние hashes и findings сохраняются.

## Повторный запуск и новая ревизия

Повтор проверки одного immutable dataset допустим. Замена файлов, labels,
grouping или usage mode создаёт новую dataset identity и новую revision.

## Защита данных и конфиденциальность

Передача использует согласованные encryption, destination, recipients и
retention. Provider не помещает raw PCAP или labels в Git и не публикует
идентификаторы организации по умолчанию.

## Ограничения интерпретации

Полный manifest не доказывает репрезентативность. Непроверяемый overlap
остаётся limitation вместе с provider attestation.

## Контрольный список

- [ ] используется только PCAP;
- [ ] usage mode выбран один;
- [ ] права и цель проверены;
- [ ] identity, provenance и grouping заполнены;
- [ ] labels отделены;
- [ ] manifests и hashes воспроизводимы;
- [ ] contamination checks выполнены;
- [ ] privacy/secrets/payload checks пройдены;
- [ ] sample plan одобрен;
- [ ] retention и deletion определены;
- [ ] inputs переданы operator, labels — custodian.

## Связанные документы

- [Data acceptance policy](data_acceptance_policy.md)
- [Передача данных](data_transfer_requirements.md)
- [Хранение и удаление](retention_and_deletion_requirements.md)
- [Правовой checklist](legal_requirements_checklist.md)
- [Data policy JSON](../../ml/reports/v0_3_18/data_acceptance_policy.json)
- [Contamination policy](../../ml/reports/v0_3_18/contamination_policy.json)
- [Dataset identity schema](../../external_review/contracts/external_dataset_identity_v1.schema.json)
