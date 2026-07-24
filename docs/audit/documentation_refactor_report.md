---
maintenance_status: completed
authoritative_status: ../status/project-status.yaml
baseline_head: c81873c72a0586bb81ba72bd035d67f75e7a20a5
---

# Итог переработки документации после v0.3.18

## Результат

Documentation maintenance полностью завершён. Это редакционный и технический
проход после v0.3.18, а не v0.3.19 и не новый научный этап. Readiness,
candidate, contracts, runtime и backend не изменены.

## Количественные показатели

| Показатель | Значение |
|---|---:|
| Проверено исходных Markdown-документов | 152 |
| Переписано существующих Markdown-документов | 25 |
| Создано новых Markdown-документов | 35 |
| Объединено прежних входных документов через redirect notes | 5 |
| Удалено дубликатов | 0 |
| Исправлено изначально сломанных ссылок | 0 |
| Устранено устаревших статусных контекстов | 7 |
| Markdown-документов после прохода | 187 |

Изначально сломанных локальных ссылок не было. Работа со ссылками состояла в
добавлении навигации и перенаправлении прежних входных страниц, поэтому
показатель исправленных broken links равен нулю.

## README: до и после

Исходный README содержал 99 строк, смешивал текущий статус, длинную историю и
разрозненные сведения. Новый README содержит 297 строк и служит самостоятельной
входной страницей: статус, назначение, архитектура, подтверждённый scope,
запреты, candidate, ключевые этапы, external review, структура репозитория,
quick start, документация, безопасность, воспроизводимость, тестирование и
roadmap.

Полная хронология вынесена в `docs/status/version-history.md`; README не
представляет v0.3.17.1 как текущий этап и не разрешает внешний trial.

## Новая архитектура документации

- `docs/getting-started/` — вход, окружение, тесты и карта репозитория;
- `docs/architecture/` — компоненты, data flow, state, события и trust
  boundaries;
- `docs/research/` — методология, causal features, lineage, evaluation,
  uncertainty и reproducibility;
- `docs/status/` — единый текущий статус, capabilities, запреты, следующий
  этап и version history;
- `docs/external_review/` — человекочитаемый пакет независимой проверки;
- `docs/contracts/`, `docs/protocols/`, `docs/reports/` — тематические индексы;
- `docs/history/` — хронология, corrections и архивная навигация;
- `docs/contributing/` — стиль, терминология и правила проверки;
- `docs/audit/` — инвентаризация и итог maintenance.

Корневые точки входа: `README.md`, `docs/index.md` и
`docs/status/project-status.yaml`.

## Авторитетные источники

Machine-readable статус хранится только в
`docs/status/project-status.yaml`. Человекочитаемое представление находится в
`docs/status/current-status.md`. Результат v0.3.18 подтверждается его policy
result, summary и frozen bundle. Redirect notes не объявлены авторитетными.

## Сохранность historical evidence

Сравнение с baseline HEAD не выявило изменений в frozen protocols, завершённых
policy results, bundle manifests и SHA-256, candidate manifests, registry
commitments, historical ledgers, контрактах внешней проверки и отчётах,
включённых в evidence bundles. Backend tree сохранил hash
`04218a4eb01534950efd5f7d6390f1a575cacbc8`.

## Проверки

- documentation maintenance validator: passed, 187 Markdown, 0 findings;
- общий documentation validator: passed;
- status consistency: passed, 28 этапов;
- internal links и anchors: 0 findings;
- absolute local paths: 0 findings;
- privacy и secret scan: 0 findings;
- orphan current docs: 0 findings;
- duplicate authoritative status: 0 findings;
- historical immutability: passed;
- repository artifact exclusion: passed;
- v0.3.18 artifact exclusion: passed, 2224 tracked files;
- v0.3.18 documentation package: passed, 18 документов;
- v0.3.18 bundle: passed, 41 artifact и 26 обязательных отчётов;
- v0.3.17 и v0.3.17.1 documentation validators: passed;
- compileall: 6 из 6;
- full pytest: 1313 passed, 0 failed, 0 skipped, 3 warnings.

Первый pytest-прогон получил 92 setup errors из-за недоступного системного
temporary-каталога и отдельно выявил три устаревших compatibility-ожидания.
Повторный полный прогон с отдельным basetemp завершился успешно. Три warnings
остались исторически известными предупреждениями scikit-learn о составе
классов в synthetic metric tests.

## Известные ограничения

Maintenance не выполнял внешний review, trial, real traffic capture,
scientific external validation, backend integration или production actions.
Удалённая ссылка не обновлялась сетевой операцией. Тяжёлые runtime artifacts не
добавлялись в Git.

## Незавершённые действия

Действий внутри documentation maintenance не осталось. Push не выполнялся.
Следующий допустимый этап остаётся v0.3.19 и ограничен независимым review
внешнего пакета и согласованием trial plan.
