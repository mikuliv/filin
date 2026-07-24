# Технические требования к передаче данных

## Граница применения

Документ используется только при планировании. Реальная передача внешнего
dataset в текущем статусе не разрешена.

## До передачи

- подтвердить legal basis и usage mode;
- определить owner, source и destination;
- перечислить recipients и access;
- выбрать encryption и transfer method;
- определить retention/deletion;
- разделить input и label namespaces;
- создать file manifest с sizes и SHA-256;
- исключить credentials и private keys.

## Передача

1. Зафиксировать sender/receiver pseudonyms.
2. Передать только allowlisted files.
3. Не объединять blind inputs и labels.
4. Не использовать внешний route, не предусмотренный plan.
5. Записать chronology event.
6. На принимающей стороне пересчитать hashes.

## После передачи

Receiver подтверждает file count, sizes, hashes и destination. Mismatch
останавливает процесс; повтор не выполняется поверх повреждённого namespace.
Logs не должны раскрывать secrets.

## Ошибки

Corruption, unknown file, wrong recipient или loss of encryption фиксируются
как incident. Материалы изолируются, а продолжение требует review. Изменение
manifest после commitment означает новую revision.

## Связанные документы

- [Руководство provider](data_provider_guide.md)
- [Правовой checklist](legal_requirements_checklist.md)
- [Retention](retention_and_deletion_requirements.md)
- [Data acceptance](data_acceptance_policy.md)
- [Текущий статус](../status/current-status.md)
