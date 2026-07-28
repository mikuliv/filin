# Лабораторная консоль

## Назначение

Локальный интерфейс каталога карточек, reconstruction views и сохраняемого ручного review.

## Статус

`current`, `laboratory-only`, этапы `v0.4.3–v0.4.4`.

## Место в архитектуре

Консоль читает incident card bundles после `incident_reconstruction/` и хранит
operator overlay отдельно от source evidence.

## Основные каталоги и файлы

- `app.py` и `__main__.py` — localhost application/CLI;
- `presentation/` и `templates/` — operator views;
- `static/` — CSS/JavaScript;
- `cases/` — каталог 12 synthetic cases;
- `contracts/` — UI, card и workflow schemas;
- `database.py` и `review.py` — SQLite overlay;
- `adapters.py` — read-only source adapters.

## Разрешённые входы

Только allowlisted laboratory case bundles и frozen reports. Token передаётся через
`FILIN_CONSOLE_TOKEN`; host должен оставаться `127.0.0.1`.

## Выходы

HTML/API views, review progress, notes, decision history и deterministic export.
Изменяемые данные пишутся в `runtime/lab_console/`.

## Страницы и API

UI: catalog, overview, facts, timeline, graph, gaps, hypotheses, comparisons,
questions, review и export. API routes versioned под `/api/console/v1/`.

## Границы и запреты

Консоль не является backend/SIEM, не меняет frozen artifacts, не определяет истинную
hypothesis и не выполняет network action. Operator notes не являются evidence.

## Безопасный запуск

```powershell
$env:FILIN_CONSOLE_TOKEN = "локальный-одноразовый-токен"
python -m lab_console --host 127.0.0.1 --port 8043
```

## Тестирование

```powershell
python -m tools.lab_console.verify_console
python -m tools.lab_console.verify_v044
python -m tools.lab_console.verify_v045
python -m pytest ml/tests/test_v043_lab_console.py ml/tests/test_v0431_console_ui.py ml/tests/test_v044_operator_cycle.py -q
```

## Источники истины

`contracts/v0_4_3/`, `contracts/v0_4_4/`, frozen policy/manifest v0.4.4 и
[operator guide](../docs/getting-started/reviewing-laboratory-cards.md).

## Каталог запусков v0.4.5

Раздел «Лаборатория» предоставляет каталог запусков, мастер замораживания плана, явное восстановление, проверку reproducibility, каталог версий кандидатов и сравнения с обязательным comparability gate. Выполнение ограничено встроенными offline-процедурами; произвольные команды, пути, сеть, обучение и автоматическое продвижение отсутствуют. Контракты находятся в `contracts/v0_4_5/`, а операторские инструкции — в [руководстве по повтору](../docs/getting-started/running-laboratory-replays.md).
