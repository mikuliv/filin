# Локальное окружение

## Требования

- Git;
- поддерживаемая версия Python, указанная в `pyproject.toml`;
- PowerShell для приведённых команд Windows;
- Docker только для специально обозначенных локальных сценариев репетиции.

## Подготовка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Не устанавливайте зависимости из неизвестных источников и не добавляйте secrets
в repository files. Сетевой доступ требуется только если пакеты отсутствуют в cache.

## каталог среды выполненияи

Тесты и console создают файлы под `runtime/`. Они не являются Зафиксировано подтверждающие материалы и
не должны попадать в коммит без отдельного documented process.

## Проверка

```powershell
python -m compileall collectors incident_reconstruction lab_console ml staging tools
python -m pytest -q
```

Ожидается `0 failed`; точное число успешных тестов относится к конкретному запуску.

См. [справочник команд](../reference/command-reference.md) и
[устранение неполадок](troubleshooting.md).
