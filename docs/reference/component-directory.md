# Каталог компонентов

| Компонент | README | Контракты | Тестирование |
|---|---|---|---|
| серверная часть prototype | [серверная часть](../../backend/README.md) | исторический серверная часть schemas | исторический tests |
| Сборщики | [Сборщики](../../collectors/README.md) | `collectors/**/contracts` | collector pytest |
| Наборы данных | [Наборы данных](../../datasets/README.md) | происхождение metadata | documentation/data tests |
| Lab | [lab](../../lab/README.md) | scenario/environment specs | lab pytest |
| ML | [ml](../../ml/README.md) | features, protocols, artifacts | full ML pytest |
| Staging | [staging](../../staging/README.md) | `staging/contracts` | staging tests |
| Rehearsal | [rehearsal](../../rehearsal/README.md) | `rehearsal/contracts` | rehearsal tests |
| Reconstruction | [`incident_reconstruction`](../../incident_reconstruction/README.md) | `incident_reconstruction/contracts` | v0.4.0–v0.4.2 tests |
| Console | [`lab_console`](../../lab_console/README.md) | `lab_console/contracts` | v0.4.3–v0.4.4 tests |
| External рассмотрение | [`external_review`](../../external_review/README.md) | `external_review/contracts` | v0.3.18 validators |
| Tools | [tools](../../tools/README.md) | tool-specific CLI | documentation/комплект validators |

Архитектурные связи приведены в [component map](../architecture/component-map.md).

Лицензионный контур: [tools/licensing](../../tools/licensing) формирует происхождение, dependency/container registries, repository манифест, notices, SBOM и проверяет distribution profiles полностью offline.
