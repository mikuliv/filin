# Текущий статус проекта

Единственный машинно-читаемый источник: [`status/project-status.yaml`](status/project-status.yaml).

- Текущий frozen candidate: v0.3.11.
- Последний independent model holdout: v0.3.13.
- Последний runtime trial: v0.3.15.
- Последний corrective audit: v0.3.15.1.
- Текущий завершённый этап: v0.3.15.1.
- Следующий разрешённый этап: отсутствует.
- Заблокированный план: v0.3.16 staging connector readiness.
- Production, shadow mode, backend integration и automatic enforcement: запрещены.
- External validation: не выполнена.

v0.3.15.1 исправил passive runtime и подтвердил целостность исторического bundle, но не подтвердил, что исходный v0.3.15 execution path действительно выполнял все заявленные fault/recovery проверки. Поэтому readiness v0.3.16 не переносится из исторического policy result.

См. [reassessment v0.3.14](experiments/v0_3_14_errata.md), [описание v0.3.15](experiments/v0_3_15.md) и [корректирующий аудит v0.3.15.1](experiments/v0_3_15_1.md).

## Планируемые подсистемы

| Компонент | Статус |
| --- | --- |
| MITRE ATT&CK mapping | Запланировано |
| Backend model integration | Не начато |
| SIEM integration | Запланировано |
| Production validation | Не выполнено |
