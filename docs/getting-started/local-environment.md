# Локальное окружение

Инструкция предназначена для чтения, разработки и безопасных контрактных проверок. Она не разрешает промышленное развёртывание, подключение к реальным сетям или научную кампанию Phase 1.

## Что действительно есть в репозитории

В корне нет `requirements.txt`, `pyproject.toml` или единого файла фиксации зависимостей. Зависимости разделены по подсистемам: `backend/requirements.txt`, `ml/requirements.txt`, `lab_console/requirements.txt`, файлы сервисов в `lab/docker/services/` и `lab/network_validation/requirements.lock`. Устанавливайте только тот набор, который нужен выбранной проверке.

Общие требования: Git, Python 3.12 или совместимый интерпретатор, а для проверок Docker — Docker Engine и Compose plugin. Зависимости сетевого контура закреплены версиями в `lab/network_validation/requirements.lock`.

## Windows и PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r lab/network_validation/requirements.lock
python -m tools.docs.validate_documentation_v2 --strict
```

Если политика PowerShell запрещает активацию, используйте `\.venv\Scripts\python.exe` явно. Для документационных тестов нужны как минимум `PyYAML` и `pytest`; сетевой пакет добавляет `numpy`, `pandas`, `joblib` и `scikit-learn`.

## Fedora/Linux, bash

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r lab/network_validation/requirements.lock
python -m tools.docs.validate_documentation_v2 --strict
```

Docker и Compose устанавливаются системным способом Fedora/Linux. Проверка принадлежности пользователя к группе Docker и настройка capability контейнеров — отдельная операционная процедура; не добавляйте Docker socket в контейнер клиента или цели.

## Каталоги результатов

Обычные тесты и консоль могут создавать файлы в `runtime/`; это изменяемый локальный слой, не подтверждающие материалы. Научный сетевой запуск имеет отдельные output-root и secret-root и не должен направляться в tracked repository.

## Проверка среды без выполнения науки

```powershell
python -m compileall backend collectors incident_reconstruction lab lab_console ml rehearsal staging tools
python -m tools.docs.validate_documentation_freshness --strict
python -m tools.docs.validate_documentation_links
```

Команда `python -m lab.network_validation.cli --help` безопасна после установки зависимостей. Команды чтения контрактов и dry-run перечислены в [справочнике команд](../reference/command-reference.md). Команды, запускающие единицу Phase 1, создание PCAP, mapping, меток, прогнозов или метрик, намеренно не приводятся как инструкция установки.

## Если установка не удалась

Зафиксируйте ОС, версию Python, точную команду и первое сообщение об ошибке. Не заменяйте версии на произвольные и не редактируйте файл фиксации зависимостей ради прохождения теста. См. [устранение неполадок](troubleshooting.md).
