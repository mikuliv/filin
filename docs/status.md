# Текущий статус проекта

Статус v0.3.16: isolated staging connector и reference receiver завершены положительно. Revision 1 корректно инвалидирован из-за ошибочного anchor; revision 2 передал 2 280/2 280 событий через две internal mTLS/TLS 1.3 границы и прошёл 24/24 faults. Разрешён только локальный controlled rehearsal v0.3.17.

Единственный машинно-читаемый источник: [`status/project-status.yaml`](status/project-status.yaml).

- Текущий development candidate: v0.3.15.4 (`v03154:65a3dd912d845bc1`).
- Последний independent model holdout: v0.3.15.5.
- Последний runtime trial: v0.3.15.5.1.
- Последний corrective audit: v0.3.15.1.
- Текущий завершённый этап: v0.3.16.
- Последний regression analysis: v0.3.15.3, анализ успешно завершён.
- Последний staging transport trial: v0.3.16.
- Следующий разрешённый этап: v0.3.17 controlled local shadow rehearsal.
- Production, shadow mode, backend integration и automatic enforcement: запрещены.
- External validation: не выполнена.

v0.3.15.1 исправил passive runtime и подтвердил целостность исторического bundle, но не подтвердил, что исходный v0.3.15 execution path действительно выполнял все заявленные fault/recovery проверки. Поэтому readiness v0.3.16 не переносится из исторического policy result.

v0.3.15.4 выполнил Track E на новом development corpus: исправил наблюдаемые сценарии и feature semantics, обучил новый candidate в пределах замороженного поиска и прошёл единственный закрытый internal audit. Это не независимый holdout. Следующий допустимый этап — v0.3.15.5; v0.3.16 остаётся заблокирован.

См. [reassessment v0.3.14](experiments/v0_3_14_errata.md), [описание v0.3.15](experiments/v0_3_15.md) и [корректирующий аудит v0.3.15.1](experiments/v0_3_15_1.md).

## Планируемые подсистемы

| Компонент | Статус |
| --- | --- |
| MITRE ATT&CK mapping | Запланировано |
| Backend model integration | Не начато |
| SIEM integration | Запланировано |
| Production validation | Не выполнено |
