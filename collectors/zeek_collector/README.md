# Сборщик Zeek

## Назначение и статус

Текущий лабораторный collector для предусмотренных Zeek logs.

## Место в архитектуре

Формирует observations, из которых строится `network_features_v2`.

## Основные файлы, входы и выходы

Parser и normalization code принимают controlled Zeek fixtures и возвращают typed records.

## Границы и запреты

Не является промышленная эксплуатация sensor agent; неизвестные schemas должны отклоняться.

## Безопасный запуск и тестирование

```powershell
python -m pytest collectors/zeek_collector -q
```

## Источники истины

Code, tests и [Сборщики overview](../README.md).
