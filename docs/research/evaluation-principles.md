# Принципы оценки

## До запуска

Фиксируются область применимости, candidate, data разбиение, seed namespace, contracts, показатели,
absolute gates, relative comparisons, stop conditions и prohibited adaptation.

## Во время запуска

Run journal сохраняет команды, environment identity, timestamps и failures.
Непредусмотренный input отклоняется. Missing подтверждающие материалы не заменяется предположением.

## После запуска

Policy result выводится из Зафиксировано gates. манифест и detached SHA связывают artifacts.
утверждение ledger показывает, какой артефакт поддерживает каждое утверждение.

## Отрицательный результат

Failure сохраняется и ограничивает следующий stage. Corrective stage не переписывает
историческую policy; он создаёт новый protocol и новые подтверждающие материалы.

## Лабораторная линия

Успех v0.4 означает корректность предусмотренной reconstruction/operator procedure,
а не новое подтверждение качества модель на внешних данных.
