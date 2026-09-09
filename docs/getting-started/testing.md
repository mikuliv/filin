# Руководство по тестированию

Тесты подтверждают отдельные контракты, целостность и воспроизводимость. Код завершения `0` относится только к конкретной команде и не расширяет научные утверждения.

## Быстрый безопасный проход

```powershell
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.validate_documentation_freshness --strict
python -m tools.docs.validate_russian_narrative --strict
python -m tools.docs.validate_documentation_links --strict
python -m tools.docs.validate_documentation_identifiers --strict
python -m tools.docs.validate_documentation_cli --strict
python -m pytest ml/tests/test_documentation_maintenance.py ml/tests/test_documentation_links.py ml/tests/test_documentation_structure.py ml/tests/test_documentation_status_consistency.py ml/tests/test_documentation_metrics_consistency.py ml/tests/test_documentation_language_v3.py ml/tests/test_documentation_identifiers.py ml/tests/test_documentation_cli.py -q
```

Эти проверки не запускают научную кампанию. Для сетевого контура дополнительно безопасны статические контрактные тесты `test_network_validation_infrastructure.py` и `test_network_validation_phase1_runtime.py`; перед запуском проверьте, что тест не вызывает Docker исполнитель или создание научных выходов.

## Инвентаризация

После содержательной редакции сначала пересоберите индексы, затем языковую опись и последней общую документационную опись. После этого выполните валидаторы. Проверка защищённых байтов обязательна. Исторические и защищённые файлы не исправляются ради языкового сканера.

## Baseline полной регрессии

Не используется обещание «0 сбоев» без привязки к конкретному окружению. Авторитетное исходное состояние хранит четыре поля: `full_regression_passed=false`, `new_regressions_detected=false`, `allowed_baseline_failures=1`, `known_baseline_change=historical_v03155_result_changed`. Перед новым запуском фиксируются точные количества пройденных, непройденных и пропущенных тестов, предупреждения и версии зависимостей. Одно разрешённое исходное отклонение не скрывает новых ошибок.

## Лабораторная консоль

```powershell
python -m tools.lab_console.verify_console
python -m tools.lab_console.verify_v044
python -m tools.lab_console.verify_v045
python -m tools.lab_console.verify_v046
python -m tools.lab_console.verify_v047
```

Это локальные проверки лабораторной линии. Они не регистрируют кандидата и не заменяют внешнюю сетевую проверку.

## Запреты

Не изменяйте защищённые протоколы, реестры, манифесты, PCAP, журналы Zeek, данные сопоставления и исторические результаты. Не запускайте `run-one-phase1-session`, инициализацию кампании, раскрытие меток, обучение, прогнозы или метрики в рамках обычной проверки. Научное выполнение требует нового официального пакета и отдельного явного разрешения.
