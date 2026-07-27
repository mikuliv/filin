---
doc_schema: filin_document_v2
title: Сопровождение документации
document_type: guide
audience:
  - contributor
lifecycle: current
authoritative_for:
  - documentation_maintenance_process
source_of_truth:
  - tools/docs
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Сопровождение документации

## Порядок

1. Проверить branch, HEAD и clean tree.
2. Построить protected set из manifests/ledgers/protocols/detached SHA.
3. Снять inventory и SHA baseline.
4. Классифицировать current, historical, redirect, generated и frozen documents.
5. Изменять только mutable files.
6. Обновить links, indexes и status views.
7. Перестроить inventory.
8. Выполнить validators, campaigns и full pytest.
9. Проверить protected bytes и clean diff.

## Frozen conflict

Если устаревший документ защищён manifest, создайте новую редакцию или errata.
Не добавляйте front matter и не исправляйте опечатку внутри frozen bytes.

## Перемещение

Сохраняйте redirect при incoming links, историческом упоминании, contractual path
или внешнем использовании. Обновляйте migration report.

## Завершение

Maintenance commit не меняет research status, candidate identity или allowed stages.
