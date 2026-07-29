# Операторский цикл рассмотрения

порядок работы состоит из overview, facts, временная последовательность, graph, разрывы, гипотезы, comparisons,
questions и decision. Progress и unresolved items сохраняются между sessions.

## изменяемый слой

Manual item states, notes и final summary находятся в SQLite изменяемый слой. исходный артефакт
identity включается в session и экспорт, но исходные bytes остаются только для чтения.

## Завершение

Operator подтверждает Контрольный список, limitations и next manual step. Допустим итог без
окончательного определения. экспорт воспроизводим для одного состояния рассмотрение.

## Запреты

порядок работы не меняет hypothesis score, не закрывает gap без нового подтверждающие материалы, не
разрешает automatic response и не превращает operator note в факт.

Практическая последовательность приведена в [руководстве](../getting-started/reviewing-laboratory-cards.md).
