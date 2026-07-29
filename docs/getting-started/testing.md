# Руководство по тестированию

## Назначение

Проверки подтверждают контракты, воспроизводимость и целостность проекта. Успешный тест не расширяет научные утверждения, не отменяет ограничения этапа и не разрешает промышленное применение.

## Предварительные условия

Запускайте команды из корня репозитория в автономной среде с установленными зависимостями. Не изменяйте зафиксированные наборы ради прохождения проверки. Временные результаты должны попадать в `runtime/` или каталог pytest.

## Быстрая проверка

```powershell
python -m pytest ml/tests/test_research_state.py ml/tests/test_documentation_status_consistency.py -q
python -m tools.docs.validate_russian_narrative --strict
```

Ожидаемый результат — код завершения `0` и отсутствие ошибок.

## Полная регрессия

```powershell
python -m pytest -q
python -m compileall backend collectors incident_reconstruction lab_console ml rehearsal staging tools
```

Число успешно пройденных тестов меняется по мере развития проекта; нормативным является `0 failed`. Предупреждение допустимо только тогда, когда оно перечислено и объяснено в отчёте конкретного запуска.

## Документация и русскоязычная редактура

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.validate_documentation_authority
python -m tools.docs.validate_documentation_freshness
python -m tools.docs.validate_documentation_immutability
python -m tools.docs.validate_documentation_terminology
python -m tools.docs.validate_russian_narrative --strict
python -m tools.docs.run_russian_narrative_campaign
```

Инвентаризацию пересобирают после содержательной редакции. Сканер обязан принимать положительные примеры и отклонять отрицательные; перечень разрешённых технических идентификаторов не должен превращаться в общий шаблон-исключение.

## Проверки лабораторной консоли

```powershell
python -m tools.lab_console.verify_console
python -m tools.lab_console.verify_v044
python -m tools.lab_console.verify_v045
python -m tools.lab_console.verify_v046
python -m tools.lab_console.verify_v047
python -m pytest ml/tests/test_v044_operator_cycle.py -q
```

Ручная приёмка в браузере проводится отдельно на поддерживаемых размерах окна. Проверяются отсутствие переполнения, понятность статусов, клавиатурный фокус, восстановление состояния и отсутствие раскрытия слепых данных.

## Разбор ошибок

1. Сохраните точную команду, код завершения и первое содержательное сообщение.
2. Определите, относится ли ошибка к коду, среде, данным или устаревшему индексу.
3. Исправляйте источник проблемы, а не ожидаемый результат и не зафиксированное доказательство.
4. Повторите узкую проверку, затем полный набор.

Если проверка неизменности сообщает только `protected_set_stale` после добавления новых документов, пересоберите инвентаризацию и повторите проверку. Несовпадение хеша уже защищённого файла является блокирующей ошибкой.

## Ограничения и запреты

Тесты не используют сеть, не запускают произвольные команды через интерфейс, не регистрируют и не продвигают кандидата. Нельзя скрывать ошибки, ослаблять контракты, переписывать исторические результаты или выдавать лабораторную проверку за внешнюю валидацию.

Точные свойства команд приведены в [справочнике команд](../reference/command-reference.md).
