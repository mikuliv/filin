# Практическое применение политики приёма данных

## Авторитетный источник

Правила определяет frozen
[data acceptance policy](../../ml/reports/v0_3_18/data_acceptance_policy.json).
Этот документ объясняет применение и не добавляет форматы или thresholds.

## Допустимый input

Поддержан только PCAP. NetFlow, CSV features и raw event rows отклоняются без
отдельной реализации. Usage mode выбирается ровно один:
`frozen_external_evaluation`, `authorized_development` или
`synthetic_protocol_rehearsal`.

## Последовательность приёма

1. Проверить ownership, legal basis placeholder и usage mode.
2. Проверить capture period, origin и pseudonymous environment.
3. Проверить grouping: episode, time range, node, environment, organization,
   capture origin.
4. Проверить taxonomy, label provenance и creation method.
5. Проверить anonymization, payload и credentials.
6. Проверить personal data, malware, encryption и transfer.
7. Проверить retention, deletion и publication restrictions.
8. Проверить manifests и overlap attestation.
9. Убедиться, что sample plan одобрен до commitment.
10. Зафиксировать accept/reject без изменения source.

## Минимальное техническое качество

PCAP должен разбираться, содержать timestamps, иметь stable capture origin,
непустой episode manifest и заранее mapped taxonomy.

## Независимость

Random split feature rows не доказывает независимость. Применяются exact,
normalized, episode/session, time/node/organization и seed/template overlap
checks из contamination policy.

## Основания отклонения

Unsupported format, missing provenance, unclear usage right, credential или
privacy finding, prohibited payload, malware, manifest mismatch, detected
overlap и unapproved sample plan приводят к fail-closed rejection.

## Результат применения

Сохраняются решение, dataset identity, manifests, attestations, выявленные
limitations и проверивший actor. Принятие данных не разрешает trial execution.

## Работа с расхождениями

До commitment исправленный manifest получает новую версию. После commitment
изменение dataset требует новой revision. Непроверяемый overlap не считается
отсутствующим: он документируется как limitation.

## Связанные документы

- [Руководство provider](data_provider_guide.md)
- [Передача данных](data_transfer_requirements.md)
- [Stop conditions](stop_conditions.md)
- [Contamination policy](../../ml/reports/v0_3_18/contamination_policy.json)
- [Dataset identity schema](../../external_review/contracts/external_dataset_identity_v1.schema.json)
- [Текущий статус](../status/current-status.md)
