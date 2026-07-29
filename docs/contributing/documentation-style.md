# Единый стандарт документации

## Язык и терминология

человекочитаемый narrative пишется по-русски. Technical identifiers, paths, commands,
fields и standards сохраняются. При первом употреблении special English term получает
русское пояснение. Используйте [глоссарий](../reference/glossary.md).

## Заголовки

Один H1 на документ. Уровни не пропускаются. Названия описывают предмет, а не номер
задачи. Links на anchors проверяются validator.

## текущий и исторический

текущий document описывает только действующее состояние. исторический result не
удаляется, но получает явный lifecycle и не используется как текущий execution path.

## Авторитетность

`authoritative_for` используется только для уникальной доменной точки входа.
машиночитаемый status и Зафиксировано policy всегда имеют приоритет над narrative.

## Утверждения и подтверждающие материалы

Каждый capability утверждение указывает stage, область применимости, подтверждающие материалы и limitation. Нельзя
превращать laboratory result в external/промышленная эксплуатация утверждение.

## Ссылки и code blocks

Используйте относительные repository links. Absolute local paths, secrets и personal
data запрещены. Команда должна существовать и указывать рабочий каталог/side effects.

## Диаграммы

Mermaid применяется только когда упрощает flow, boundary или lifecycle. Diagram
не должна создавать причинную семантику, отсутствующую в contract.

## Служебный заголовок

Редактируемый canonical текущий document использует:

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

Зафиксировано files не меняются ради metadata.

## Генерируемые документы

Указываются `generated: true`, source paths, generator version и reproduction command.
Generated area ограничивается `<!-- generated:start -->` и `<!-- generated:end -->`.

## README подсистемы

Обязательны назначение, status, место в architecture, files, inputs, outputs,
boundaries, safe run, testing, sources of truth и related docs.

## перенаправление

перенаправление содержит Служебный заголовок, один H1, canonical link, причину, lifecycle и явное
отсутствие authority. Он не повторяет прежние capability markers.

## Документация этапа

Новый stage обновляет protocol/report indexes, status реестр, limitations и
next-stage только после policy result. Зафиксировано reports задним числом не редактируются.

## Проверка

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
```

Для нового документа также проверьте лицензионный область применимости: документация обычно получает CC-BY-4.0 через `REUSE.toml`, а вставки сторонних схем, изображений и текста требуют отдельного происхождение и исходной лицензии. Зафиксировано подтверждающие материалы нельзя менять ради SPDX header.
