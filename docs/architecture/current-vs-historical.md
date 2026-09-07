# Текущие и исторические компоненты

## Текущие

- история происхождения кандидата и `network_features_v2`;
- контракт пассивного события (`shadow_event_v2`);
- staging/reference receiver как изолированный лабораторный transport;
- `incident_reconstruction/` в состоянии `v0.4.0–v0.4.4`;
- `lab_console/` и operator порядок работы v0.4.4;
- `lab/network_validation/` как технический контур Phase 1: 288 шаблонов, 864
  единицы выполнения, 24 пары и 51 признак;
- официальный пакет v4 как последний зафиксированный пакет, отдельно от более
  нового текущего кода среды выполнения с исправлением запуска Zeek.

## Исторические или демонстрационные

- `backend/` и ранние incident endpoints;
- статический MITRE prototype;
- прежний Sigma generator;
- ранние модель profiles и training plans;
- superseded event contracts;
- старые интеграционные обещания, отменённые последующими policy results.
- исторически сообщённые попытки сетевой проверки, если их operational records
  отсутствуют в tracked repository.

## Старые пути документации

`docs/modeling.md`, `docs/incident-workflow.md`, `docs/mitre-mapping.md` и
`docs/sigma-generation.md` сохранены как короткие redirects к историческому слою.
Они не являются источниками текущей архитектуры.

См. [историческую серверную часть](../history/historical-backend.md),
[историческое моделирование](../history/historical-modeling.md) и
[MITRE/Sigma](../history/historical-mitre-and-sigma.md).
