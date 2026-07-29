# Сборщик Suricata

## Назначение и статус

Лабораторный adapter для предусмотренных Suricata records; не текущий промышленная эксплуатация path.

## Место в архитектуре

Поддерживает controlled comparison/fixtures рядом с основным Zeek flow.

## Основные файлы, входы и выходы

Parser принимает версионированный synthetic records и выдаёт нормализованное представление.

## Границы и запреты

Alert Suricata не считается доказательством атаки и не разрешает automatic response.

## Безопасный запуск и тестирование

```powershell
python -m pytest collectors/suricata_collector -q
```

## Источники истины

Code, tests и [Сборщики overview](../README.md).
