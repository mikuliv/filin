# Руководство по тестированию

## Общее правило

Evergreen-документация не фиксирует один «текущий» счётчик. Ожидается `0 failed`.
Фактическое количество `passed` фиксируется в отчёте конкретного запуска.

## Быстрый smoke-прогон

```powershell
python -m pytest ml/tests/test_research_state.py ml/tests/test_documentation_status_consistency.py -q
```

## Полный pytest

```powershell
python -m pytest -q
```

Полный прогон может быть длительным и пишет временные файлы в `runtime/` и pytest temp.

## Compileall

```powershell
python -m compileall backend collectors incident_reconstruction lab_console ml rehearsal staging tools
```

## Документация v2

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.run_documentation_campaign
```

## Status и candidate integrity

```powershell
python -m tools.docs.validate_project_status --strict
python -m tools.docs.validate_documentation_authority
python -m tools.docs.validate_documentation_immutability
```

## Реконструкция v0.4.0–v0.4.4

```powershell
python -m pytest ml/tests/test_v040_incident_reconstruction.py ml/tests/test_v041_temporal_reconstruction.py ml/tests/test_v042_hypothesis_analysis.py -q
python -m tools.lab_console.verify_v044
```

## Консоль

```powershell
python -m pytest ml/tests/test_v043_lab_console.py ml/tests/test_v0431_console_ui.py ml/tests/test_v044_operator_cycle.py -q
```

Browser acceptance требует локально запущенной консоли и выполняется как отдельная
ручная проверка; сохранённый frozen результат находится в `ml/reports/v0_4_4/`.

## Bundle validators

Используйте только versioned validators из `tools/audit/` и `tools/lab_console/`.
Не перегенерируйте frozen bundle ради прохождения проверки.

## Длительные runners

Campaign/rehearsal runners запускаются только по соответствующему frozen protocol.
Они не являются быстрым стартом, могут писать значительный runtime и не разрешают
production traffic.

Полные свойства команд: [command-reference](../reference/command-reference.md).
