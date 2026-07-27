# CSV collector

## Назначение и статус

Текущий лабораторный adapter для versioned CSV fixtures.

## Место в архитектуре

Преобразует разрешённые columns в нормализованные observations перед feature pipeline.

## Основные файлы, входы и выходы

Parser, schema validation и tests находятся в каталоге. Вход — synthetic CSV по
известному contract; выход — typed records.

## Границы и запреты

Не допускаются произвольные personal datasets, silent column mapping и production ingest.

## Безопасный запуск и тестирование

```powershell
python -m pytest collectors/csv_collector -q
```

## Источники истины

Code, tests и collector contracts; общий обзор — [collectors](../README.md).
