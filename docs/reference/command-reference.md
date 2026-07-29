# Справочник команд

Все команды выполняются из корня репозитория. Поле «изменения» описывает ожидаемую запись на диск; ни одна команда ниже не должна обращаться к сети или менять действующего кандидата.

## Основные проверки

| Команда | Назначение | Изменения | Ожидаемый результат | Ограничение |
|---|---|---|---|---|
| `python -m pytest -q` | полная регрессия | временные файлы pytest | `0 failed` | число пройденных тестов не фиксировано |
| `python -m compileall backend collectors incident_reconstruction lab_console ml rehearsal staging tools` | проверка синтаксиса и импорта | `__pycache__` | код `0` | не заменяет функциональные тесты |
| `python -m tools.lab_console.verify_console` | базовые контракты консоли | временные файлы | проверка пройдена | только локальный режим |
| `python -m tools.lab_console.verify_v044` | операторский цикл карточек | временные файлы | проверка пройдена | не создаёт научного решения |
| `python -m tools.lab_console.verify_v045` | каталог и сравнение запусков | временные файлы | проверка пройдена | без выбора кандидата |
| `python -m tools.lab_console.verify_v046` | предложения кандидатов | временные файлы | проверка пройдена | без регистрации и продвижения |
| `python -m tools.lab_console.verify_v047` | слепая лабораторная проверка | временные файлы | проверка пройдена | без раскрытия строк и повторного вывода |

## Документация

| Команда | Назначение | Изменения | Ожидаемый результат | Ограничение |
|---|---|---|---|---|
| `python -m tools.docs.build_documentation_inventory` | пересобрать навигацию и защищённый перечень | `docs/audit/` | детерминированные индексы | запускать после редакции |
| `python -m tools.docs.validate_documentation_v2 --strict` | проверить структуру Documentation v2 | нет | `valid: true` | не исправляет файлы |
| `python -m tools.docs.validate_documentation_authority` | проверить источники истины | нет | код `0` | YAML статуса имеет приоритет |
| `python -m tools.docs.validate_documentation_freshness` | найти устаревшие ссылки и сведения | нет | код `0` | исторические документы не становятся текущими |
| `python -m tools.docs.validate_documentation_immutability` | проверить защищённые байты | нет | код `0` | несовпадение хеша блокирует этап |
| `python -m tools.docs.validate_documentation_terminology` | проверить научные замены терминов | нет | код `0` | не заменяет языковой сканер |
| `python -m tools.docs.validate_russian_narrative --strict` | проверить человекочитаемый русский текст | нет | `finding_count: 0` | код и разрешённые идентификаторы исключаются контекстно |
| `python -m tools.docs.run_russian_narrative_campaign` | проверить положительные и отрицательные примеры | временный каталог | все сценарии пройдены | примеры не входят в продуктовые данные |

## Целостность кандидата и этапов

```powershell
python -m tools.audit.validate_v03154_bundle
python -m tools.audit.validate_v0318_bundle
python -m tools.audit.validate_v040_bundle
python -m tools.audit.validate_v041_bundle
python -m tools.audit.validate_v042_bundle
```

Эти команды читают зафиксированные пакеты и сверяют контрольные суммы. Они не обучают модель, не пересобирают исторические артефакты и не меняют реестр кандидатов.

## Лицензирование

```powershell
python -m tools.licensing.validate_manifest
python -m tools.licensing.validate_frozen_license_mapping
python -m tools.licensing.validate_upstream_standard_texts
python -m tools.licensing.validate_license_files
python -m tools.licensing.validate_distribution_profiles
python -m tools.licensing.validate_third_party_notices
```

Ожидаемый результат — отсутствие файлов без назначения, конфликтов и неизвестных лицензий. Официальные тексты лицензий и зафиксированные материалы не редактируются языковой кампанией.

## Запуск консоли

```powershell
$env:FILIN_CONSOLE_TOKEN = "локальный-одноразовый-токен"
python -m lab_console --host 127.0.0.1 --port 8043
```

Команда пишет только изменяемое состояние в `runtime/lab_console/`. Запрещены внешний адрес, публикация токена, произвольные аргументы выполнения, сетевой доступ и промышленное использование.

## Полномочия результата

Код завершения `0` подтверждает только контракт конкретной команды. Он не означает внешнюю валидацию, готовность к промышленной эксплуатации, истинность гипотезы или право автоматически выбрать либо продвинуть модель.
