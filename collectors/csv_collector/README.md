# Сборщик CSV

## Назначение и статус

Текущий лабораторный adapter для версионированный CSV fixtures.

## Место в архитектуре

Преобразует разрешённые columns в нормализованные observations перед признак pipeline.

## Основные файлы, входы и выходы

Parser, schema проверка и tests находятся в каталоге. Вход — synthetic CSV по
известному contract; выход — typed records.

## Границы и запреты

Не допускаются произвольные personal Наборы данных, silent column mapping и промышленная эксплуатация ingest.

## Безопасный запуск и тестирование

```powershell
python -m pytest collectors/csv_collector -q
```

## Источники истины

Code, tests и collector contracts; общий обзор — [Сборщики](../README.md).
