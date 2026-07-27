# План переработки документации v2

## Опорное состояние

- frozen stage v0.4.4: `80680bf8e890742e1c82929d7a2e8cd099a1b1ad`;
- фактический maintenance HEAD: `e97224a3f01a40cad83f88a35df922344088dd24`;
- дополнительные commits объяснены обновлением launcher и UI;
- branch: `main`; reset/pull/merge/rebase/push запрещены;
- candidate и backend tree должны остаться неизменными.

## Классификация

Все tracked Markdown классифицируются как authoritative current, current reference,
guide, developer guide, historical, frozen evidence, redirect, generated, duplicate
или unresolved. Местоположение само по себе не определяет lifecycle.

## Защита evidence

Protected set строится динамически из manifests, protocols, ledgers, candidate
identity и detached SHA. Текущие bytes baseline фиксируются до edits. Manifest SHA
mismatches, существовавшие на входе, сохраняются как warnings.

## Информационная архитектура

Перерабатываются README, docs/index, status, architecture, getting-started,
reference, history, contributing и subsystem README. Frozen stage documents не меняются.

## Проверка

Выполняются structural/link/anchor/status/authority/immutability/terminology validators,
positive и negative campaigns, console/v0.4.4 verifiers, bundle validators,
compileall, full pytest и `git diff --check`.

## Завершение

Один итоговый commit без push. Research status, `v0.3.19` и `v0.4.5` сохраняются.
