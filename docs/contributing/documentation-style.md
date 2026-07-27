# Единый стандарт документации

## Язык и терминология

Human-readable narrative пишется по-русски. Technical identifiers, paths, commands,
fields и standards сохраняются. При первом употреблении special English term получает
русское пояснение. Используйте [глоссарий](../reference/glossary.md).

## Заголовки

Один H1 на документ. Уровни не пропускаются. Названия описывают предмет, а не номер
задачи. Links на anchors проверяются validator.

## Current и historical

Current document описывает только действующее состояние. Historical result не
удаляется, но получает явный lifecycle и не используется как current execution path.

## Авторитетность

`authoritative_for` используется только для уникальной доменной точки входа.
Machine-readable status и frozen policy всегда имеют приоритет над narrative.

## Утверждения и evidence

Каждый capability claim указывает stage, scope, evidence и limitation. Нельзя
превращать laboratory result в external/production claim.

## Ссылки и code blocks

Используйте относительные repository links. Absolute local paths, secrets и personal
data запрещены. Команда должна существовать и указывать рабочий каталог/side effects.

## Диаграммы

Mermaid применяется только когда упрощает flow, boundary или lifecycle. Diagram
не должна создавать причинную семантику, отсутствующую в contract.

## Front matter

Редактируемый canonical current document использует:

```yaml
---
doc_schema: filin_document_v2
title: Понятный заголовок
document_type: overview
audience:
  - developer
lifecycle: current
authoritative_for: []
source_of_truth:
  - path/to/source
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---
```

Frozen files не меняются ради metadata.

## Generated documents

Указываются `generated: true`, source paths, generator version и reproduction command.
Generated area ограничивается `<!-- generated:start -->` и `<!-- generated:end -->`.

## README подсистемы

Обязательны назначение, status, место в architecture, files, inputs, outputs,
boundaries, safe run, testing, sources of truth и related docs.

## Redirect

Redirect содержит front matter, один H1, canonical link, причину, lifecycle и явное
отсутствие authority. Он не повторяет прежние capability markers.

## Stage documentation

Новый stage обновляет protocol/report indexes, status registry, limitations и
next-stage только после policy result. Frozen reports задним числом не редактируются.

## Проверка

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
```
