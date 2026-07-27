# Коррекции и отрицательные результаты

## Сохранение отрицательных итогов

Environment shift, coverage, episode, runtime, privacy, performance и integrity
gates неоднократно не проходили. Эти results сохранены в исходных policy files и
не отменяются последующими успешными stages.

## Corrective stages

`v0.3.10.1`, `v0.3.12.1`, `v0.3.15.1`, `v0.3.15.3` и `v0.3.17.1` уточнили
semantics, evidence или procedures. Correction создаёт новый artifact и не меняет
исторический hash.

## Ограничение claims

Поздний audit может признать прежний readiness claim неподтверждённым. В этом случае
historical report остаётся, а current status использует более узкую формулировку.

Для точных итогов откройте [reports index](../reports/index.md).
