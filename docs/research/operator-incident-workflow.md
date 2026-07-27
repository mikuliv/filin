# Операторский цикл рассмотрения

Workflow состоит из overview, facts, timeline, graph, gaps, hypotheses, comparisons,
questions и decision. Progress и unresolved items сохраняются между sessions.

## Overlay

Manual item states, notes и final summary находятся в SQLite overlay. Source artifact
identity включается в session и export, но исходные bytes остаются read-only.

## Завершение

Operator подтверждает checklist, limitations и next manual step. Допустим итог без
окончательного определения. Export воспроизводим для одного состояния review.

## Запреты

Workflow не меняет hypothesis score, не закрывает gap без нового evidence, не
разрешает automatic response и не превращает operator note в факт.

Практическая последовательность приведена в [руководстве](../getting-started/reviewing-laboratory-cards.md).
