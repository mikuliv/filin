# Staging transport и эталонный приёмник

## Назначение

Изолированная локальная доставка `shadow_event_v2`, ACK, retry и timing traces.

## Статус

`current`, `laboratory-only`, не production backend.

## Место в архитектуре

Завершает проверенный transport основной линии перед laboratory reconstruction.

## Основные каталоги и файлы

Contracts, reference receiver, connector и tests находятся внутри `staging/`.

## Разрешённые входы и выходы

Только allowlisted passive events; outputs — validated receipts/ACK и local traces.

## Границы и запреты

Public endpoint, organization infrastructure и automatic actions запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest ml/tests/test_v0316_staging_transport.py -q
```

## Источники истины

Contracts каталога и [staging architecture](../docs/architecture/detection-and-runtime-track.md).
