# Технические требования хранения и удаления

## Граница применения

Frozen protocol не назначает универсальный срок. Сроки, legal hold и deletion
evidence согласуются сторонами и проверяются компетентным юристом.

## Категории материалов

- blind inputs и raw PCAP;
- labels и reveal packages;
- predictions;
- manifests и commitments;
- aggregate evaluation result;
- review findings и approval decision;
- logs и security incidents;
- backup copies.

## До приёма dataset

Для каждой категории определить owner, location, access, encryption, retention
trigger, deletion deadline placeholder, backup handling и legal hold.
Development data и frozen holdout хранятся раздельно.

## Во время процесса

Доступ минимизируется по роли. Копии учитываются в manifest или inventory.
Raw data не помещаются в Git. Transfer и access events журналируются без
раскрытия secrets.

## Удаление

1. Проверить завершение согласованного retention trigger.
2. Проверить отсутствие legal hold.
3. Удалить active и учтённые backup copies.
4. Сохранить допустимое deletion evidence.
5. Зафиксировать actor, scope и время.
6. Сообщить об исключениях ответственным сторонам.

## Ошибки

Невозможность подтвердить удаление, unknown copy или unauthorized retention
фиксируются как finding. Evidence об инциденте сохраняется в минимально
необходимом объёме.

## Связанные документы

- [Передача данных](data_transfer_requirements.md)
- [Правовой checklist](legal_requirements_checklist.md)
- [Руководство provider](data_provider_guide.md)
- [Publication](publication_requirements.md)
- [Текущий статус](../status/current-status.md)
