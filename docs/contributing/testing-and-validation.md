---
doc_schema: filin_document_v2
title: Проверка документации
document_type: guide
audience:
  - contributor
  - auditor
lifecycle: current
authoritative_for: []
source_of_truth:
  - tools/docs
  - ml/tests/test_documentation_maintenance.py
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Проверка документации

## Основной проход

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.run_documentation_campaign
python -m pytest ml/tests/test_documentation_maintenance.py ml/tests/test_documentation_links.py ml/tests/test_documentation_structure.py ml/tests/test_documentation_status_consistency.py -q
```

## Что проверяется

Headings, links, anchors, repository escape, front matter, current orphans, redirects,
authority, status/candidate identity, indexes, commands/routes, prohibited claims,
terminology, secrets, absolute paths, protected bytes и inventory freshness.

## Отрицательная кампания

Каждый scenario создаёт временную fixture copy, вносит одно нарушение и ожидает
конкретный error code. Passing invalid fixture считается regression.

## Итог

Ожидается `0 failed`. Exact count записывается в audit report конкретного прохода.
