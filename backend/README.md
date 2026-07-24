# Backend-прототип

`backend/` — исторический демонстрационный прототип, а не компонент текущего
сенсора и не кандидат для развёртывания.

Прототип не загружает и не обслуживает frozen candidate
`v03154:65a3dd912d845bc1`. Его confidence является эвристикой, а не
калиброванной вероятностью ML-модели. MITRE mapping, Sigma generation и
`matched_events` не подтверждены реальным поисковым или SIEM-контуром.

Backend integration запрещена: текущий sensor/runtime с этим каталогом не
связан, production connections отсутствуют, а readiness-флаги остаются
ложными. Историческое отрицательное наблюдение v0.3.3 не заменено новой
независимой evidence-базой.

См. [границы доверия](../docs/architecture/trust-boundaries.md) и
[запрещённые возможности](../docs/status/prohibited-capabilities.md).
