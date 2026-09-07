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
| Независимая сетевая проверка | [`lab/network_validation`](../../lab/network_validation/README.md) | `lab/network_validation/execution`, `config`, контракты среды выполнения | статические проверки, пробная проверка и контрактные тесты; научный запуск отдельно разрешается |
| Инструменты | [tools](../../tools/README.md) | профильный CLI | проверки документации и пакета |

Архитектурные связи приведены в [component map](../architecture/component-map.md).

Лицензионный контур: [tools/licensing](../../tools/licensing) формирует происхождение, реестры зависимостей и контейнеров, манифест репозитория, notices, SBOM и проверяет профили распространения полностью offline.

## Как выбирать источник истины

Для текущего статуса сначала читаются `docs/status/project-status.yaml` и официальный пакет с максимальным номером. Для структуры и поведения Phase 1 приоритет имеют контракты в `lab/network_validation/execution/` и фактический код. Исторические отчёты объясняют прежние решения, но не разрешают новый запуск. Страницы `docs/research/` описывают эти источники и не заменяют их.
