# Проверка документации

## Основной проход

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.run_documentation_campaign
python -m pytest ml/tests/test_documentation_maintenance.py ml/tests/test_documentation_links.py ml/tests/test_documentation_structure.py ml/tests/test_documentation_status_consistency.py -q
```

## Что проверяется

Headings, links, anchors, repository escape, Служебный заголовок, текущий orphans, redirects,
authority, status/candidate identity, indexes, commands/routes, prohibited claims,
terminology, secrets, absolute paths, protected bytes и inventory freshness.

## Отрицательная кампания

Каждый scenario создаёт временную fixture copy, вносит одно нарушение и ожидает
конкретный error code. Passing invalid fixture считается regression.

## Итог

Не используется безусловное требование `0 failed`: отчёт фиксирует `full_regression_passed`, `new_regressions_detected`, допустимый baseline и фактические числа конкретного прохода. Известное изменение baseline — `historical_v03155_result_changed`.
