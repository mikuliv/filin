# Каталог компонентов

| Компонент | README | Контракты | Тестирование |
|---|---|---|---|
| Серверная часть (прототип) | [серверная часть](../../backend/README.md) | исторические схемы серверной части | исторические тесты |
| Сборщики | [Сборщики](../../collectors/README.md) | `collectors/**/contracts` | pytest сборщиков |
| Наборы данных | [Наборы данных](../../datasets/README.md) | происхождение metadata | documentation/data tests |
| Лаборатория | [lab](../../lab/README.md) | спецификации сценариев и среды | pytest лаборатории |
| ML | [ml](../../ml/README.md) | признаки, протоколы, артефакты | полный pytest ML |
| Staging | [staging](../../staging/README.md) | `staging/contracts` | staging tests |
| Rehearsal | [rehearsal](../../rehearsal/README.md) | `rehearsal/contracts` | rehearsal tests |
| Reconstruction | [`incident_reconstruction`](../../incident_reconstruction/README.md) | `incident_reconstruction/contracts` | v0.4.0–v0.4.2 tests |
| Console | [`lab_console`](../../lab_console/README.md) | `lab_console/contracts` | v0.4.3–v0.4.4 tests |
| Внешняя проверка | [`external_review`](../../external_review/README.md) | `external_review/contracts` | проверки v0.3.18 |
| Инструменты | [tools](../../tools/README.md) | профильный CLI | проверки документации и пакета |

Архитектурные связи приведены в [component map](../architecture/component-map.md).

Лицензионный контур: [tools/licensing](../../tools/licensing) формирует происхождение, dependency/container registries, repository манифест, notices, SBOM и проверяет distribution profiles полностью offline.
