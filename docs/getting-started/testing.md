# Тестирование

## Быстрые unit tests

Для отдельной подсистемы указывается конкретный test path:

```powershell
python -m pytest -q ml/tests/test_v0318_contracts.py
```

## Полный regression suite

```powershell
python -m pytest -q
```

Последний зафиксированный результат относится к завершению v0.3.18:
`1309 passed`, `0 failed`, `0 skipped`, `3 warnings`.

## Compileall

Проверяются шесть деревьев: `ml`, `collectors`, `tools`, `lab`, `staging` и
`backend`.

```powershell
python -m compileall ml collectors tools lab staging backend
```

## Документация и status

```powershell
python tools/docs/validate_documentation.py --strict
python tools/docs/validate_project_status.py --strict
python tools/docs/validate_documentation_maintenance.py --strict
```

## Contracts и bundles

Version-specific validators находятся в `tools/audit`. Для текущего
authoritative bundle используется:

```powershell
python -m tools.audit.validate_v0318_bundle
```

External review package проверяется standalone verifier из runtime package.
Команда и package path зависят от локального runtime и намеренно не фиксируются
в документации.

## Длительные runners

Не запускать без ознакомления с соответствующим frozen protocol. Они не входят
в documentation maintenance и CI.
