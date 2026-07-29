# План переработки документации v2

## Опорное состояние

- Зафиксировано stage v0.4.4: `80680bf8e890742e1c82929d7a2e8cd099a1b1ad`;
- фактический maintenance HEAD: `e97224a3f01a40cad83f88a35df922344088dd24`;
- дополнительные commits объяснены обновлением launcher и UI;
- branch: `main`; reset/pull/merge/rebase/push запрещены;
- candidate и серверная часть tree должны остаться неизменными.

## Классификация

Все tracked Markdown классифицируются как authoritative текущий, текущий reference,
guide, developer guide, исторический, Зафиксировано подтверждающие материалы, перенаправление, generated, duplicate
или unresolved. Местоположение само по себе не определяет lifecycle.

## Защита подтверждающие материалы

Protected set строится динамически из manifests, protocols, ledgers, candidate
identity и detached SHA. Текущие bytes baseline фиксируются до edits. манифест SHA
mismatches, существовавшие на входе, сохраняются как предупреждения.

## Информационная архитектура

Перерабатываются README, docs/index, status, architecture, getting-started,
reference, history, contributing и subsystem README. Зафиксировано stage documents не меняются.

## Проверка

Выполняются structural/link/anchor/status/authority/immutability/terminology validators,
positive и negative Кампании, console/v0.4.4 verifiers, комплект validators,
Проверка компиляции, full pytest и `git diff --check`.

## Завершение

Один итоговый Коммит без push. Research status, `v0.3.19` и `v0.4.5` сохраняются.
