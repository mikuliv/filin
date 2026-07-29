# Воспроизводимость

## Идентичность

Candidate, contract, protocol, source комплект и results связываются SHA-256. Semantic
SHA фиксирует значимое содержимое там, где presentation bytes могут различаться.

## Детерминизм

Seed namespaces, canonical Файлы JSON, stable ordering и версионированный generators должны
давать одинаковые artifacts для одинакового input. среда выполнения timestamps и temp paths
не включаются в semantic identity без необходимости.

## Проверяемая цепочка

1. protocol определяет запуск;
2. run journal фиксирует выполнение;
3. policy result фиксирует итог;
4. манифест перечисляет artifacts;
5. detached SHA фиксирует манифест;
6. утверждение ledger связывает assertions с подтверждающие материалы;
7. reproduction guide даёт безопасную команду проверки.

## Ограничение

Воспроизводимость лабораторного результата не равна external validity. Зафиксировано file
нельзя исправлять задним числом; используются errata и новый обзор.

Индексы: [protocols](../protocols/index.md), [reports](../reports/index.md) и
[protected documentation](../audit/protected_documentation_v2.json).
