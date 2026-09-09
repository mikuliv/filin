# Проверка документации

## Основной проход

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.run_documentation_campaign
python -m pytest ml/tests/test_documentation_maintenance.py ml/tests/test_documentation_links.py ml/tests/test_documentation_structure.py ml/tests/test_documentation_status_consistency.py ml/tests/test_documentation_language_v3.py ml/tests/test_documentation_identifiers.py ml/tests/test_documentation_cli.py -q
```

## Что проверяется

Заголовки, ссылки, якоря, выход за пределы репозитория, служебный заголовок, текущие документы без входящих ссылок, перенаправления,
источники истины, статус и идентичность кандидата, указатели, команды и маршруты, запрещённые утверждения,
терминологию, секреты, абсолютные пути, байты защищённых файлов и актуальность описи.

## Отрицательная кампания

Каждый сценарий создаёт временную копию заготовки, вносит одно нарушение и ожидает
конкретный код ошибки. Принятие недопустимой заготовки считается регрессией.

## Итог

Не используется безусловное требование «0 сбоев»: отчёт фиксирует `full_regression_passed`, `new_regressions_detected`, допустимое исходное состояние и фактические числа конкретного прохода. Известное изменение исходного состояния — `historical_v03155_result_changed`.
