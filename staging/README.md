# Staging transport и эталонный приёмник

## Назначение

Изолированная локальная доставка `shadow_event_v2`, подтверждений приёма, повторов
и временных трасс.

## Статус

`current`, `laboratory-only`, не промышленная серверная часть.

## Место в архитектуре

Завершает проверенный transport основной линии перед laboratory reconstruction.

## Основные каталоги и файлы

Contracts, reference receiver, connector и tests находятся внутри `staging/`.

## Разрешённые входы и выходы

Только разрешённые пассивные события; результаты — проверенные квитанции,
подтверждения приёма и локальные трассы.

## Границы и запреты

Публичная конечная точка, инфраструктура организации и автоматические действия запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest ml/tests/test_v0316_staging_transport.py -q
```

## Источники истины

Contracts каталога и [staging architecture](../docs/architecture/detection-and-runtime-track.md).
