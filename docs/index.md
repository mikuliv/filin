# Документация платформы «Филин»

Лабораторный этап v0.4.7.2 завершён: [описание эксперимента](experiments/v0_4_7_2.md), [порядок подготовки предложения](getting-started/preparing-corrective-candidate-proposal.md) и [исследовательские правила](research/corrective-candidate-development.md). Следующий разрешённый лабораторный этап — только v0.4.7.3; v0.4.8 запрещён.

Эта страница — каноническая навигация по текущему устройству проекта. Исторические
отчёты и Зафиксировано подтверждающие материалы доступны через отдельные индексы и не подменяют текущий статус.

## Новый технический читатель

1. [Что такое «Филин»](getting-started/overview.md).
2. [Текущий статус двух линий](status/current-status.md).
3. [Архитектура после v0.4.4](architecture/overview.md).
4. [Подтверждённые возможности](status/confirmed-capabilities.md).
5. [Текущие ограничения](architecture/limitations.md).
6. [Следующие допустимые этапы](status/next-stage.md).

## Разработчик

1. [Точка входа разработчика](getting-started/developer-entrypoint.md).
2. [Структура репозитория](getting-started/repository-layout.md).
3. [Локальное окружение](getting-started/local-environment.md).
4. [Справочник команд](reference/command-reference.md).
5. [Тестирование](getting-started/testing.md).
6. [Каталог компонентов](reference/component-directory.md).
7. [Контракты](contracts/index.md).
8. [Правила изменений](contributing/documentation-maintenance.md).

## Оператор лабораторной консоли

1. [Запуск и вход](getting-started/laboratory-console.md).
2. [Каталог и обзор карточки](getting-started/reviewing-laboratory-cards.md#каталог-и-обзор).
3. [Временная шкала](getting-started/reviewing-laboratory-cards.md#временная-шкала).
4. [Граф](getting-started/reviewing-laboratory-cards.md#граф-реконструкции).
5. [Разрывы](getting-started/reviewing-laboratory-cards.md#разрывы-реконструкции).
6. [Гипотезы и матрица](getting-started/reviewing-laboratory-cards.md#гипотезы-и-матрица).
7. [Ручное рассмотрение](getting-started/reviewing-laboratory-cards.md#ручное-рассмотрение).
8. [Экспорт](getting-started/reviewing-laboratory-cards.md#экспорт).

## Аудитор

1. [Иерархия источников истины](reference/sources-of-truth.md).
2. [Точка входа аудитора](getting-started/auditor-entrypoint.md).
3. [Статус основной линии](status/project-status.yaml) и
   [лабораторной линии](status/v0_4_track.yaml).
4. [Зафиксированные протоколы](protocols/index.md).
5. [Итоговые отчёты и пакеты подтверждающих материалов](reports/index.md).
6. [Контракты](contracts/index.md).
7. [Воспроизводимость](research/reproducibility.md).
8. [Коррекции и отрицательные результаты](history/corrections-and-negative-results.md).
9. [Инвентаризация документации](audit/documentation_inventory_v2.md).
10. [Защищённый набор](audit/protected_documentation_v2.json).

## Независимый эксперт

1. [Граница v0.3.19](getting-started/external-review-entrypoint.md).
2. [Полное русское изложение внешнего комплекта](guides/external-review/README.md).
3. [Подтверждённая область](status/confirmed-capabilities.md).
4. [Известные ограничения](architecture/limitations.md).
5. [Роли и порядок первого контакта](getting-started/external-review-entrypoint.md#роли).
6. [Зафиксированный пакет v0.3.18](reports/index.md).

## Архитектура

- [Индекс архитектуры](architecture/index.md).
- [Сквозной поток данных](architecture/end-to-end-data-flow.md).
- [Основная линия detection/среда выполнения](architecture/detection-and-runtime-track.md).
- [Лабораторная реконструкция и анализ](architecture/reconstruction-and-analysis-track.md).
- [Лабораторная консоль](architecture/laboratory-console.md).
- [Компонентная карта](architecture/component-map.md).
- [Границы доверия](architecture/trust-boundaries.md).
- [Хранилища и артефакты](architecture/storage-and-artifacts.md).
- [Текущие и исторические компоненты](architecture/current-vs-historical.md).

## Исследовательская методология

- [Методология](research/methodology.md).
- [Причинные признаки](research/causal-features.md).
- [Линия кандидата](research/candidate-lineage.md).
- [Принципы оценки](research/evaluation-principles.md).
- [Неопределённость и отказ от решения](research/uncertainty-and-abstention.md).
- [Реконструкция инцидента](research/incident-reconstruction.md).
- [Временная реконструкция](research/temporal-reconstruction.md).
- [Конкурирующие гипотезы](research/competing-hypotheses.md).
- [Ручное рассмотрение](research/manual-incident-review.md).
- [Каталог лабораторных случаев](research/laboratory-case-catalog.md).
- [Операторский цикл](research/operator-incident-workflow.md).
- [Анализ причин отрицательной проверки](research/failed-validation-root-cause-analysis.md).
- [Автономность лабораторной линии](research/laboratory-track-autonomy.md).
- [Управление данными после раскрытия разметки](research/post-blind-data-governance.md).
- [Рассмотрение отрицательного результата](getting-started/reviewing-failed-validation.md).

## Справочники

- [Глоссарий](reference/glossary.md) и [терминология](reference/terminology.md).
- [Жизненный цикл документов](reference/document-lifecycle.md).
- [Типы артефактов](reference/artifact-types.md).
- [Статусы](reference/status-values.md).
- [Коды результатов и ошибок](reference/error-and-result-codes.md).
- [Полная история версий](status/version-history.md).
- [Исторический архив](history/index.md).

## Сопровождение документации

- [Единый стиль](contributing/documentation-style.md).
- [процесс обслуживания](contributing/documentation-maintenance.md).
- [Проверка документации](contributing/testing-and-validation.md).
- [Добавление этапа](contributing/adding-a-stage.md).
- [Добавление контракта](contributing/adding-a-contract.md).
- [Добавление отчёта](contributing/adding-a-report.md).
- [README подсистемы](contributing/adding-a-subsystem-readme.md).
- [материалы аудита текущей переработки](audit/index.md).

## Лицензирование и распространение

- [Центр лицензионной документации](licensing/index.md).
- [Профили распространяемого состава](licensing/distribution-profiles.md).
- [Сторонние компоненты](licensing/third-party-components.md).
- [Контрольный список релиза](licensing/release-checklist.md).

## Воспроизводимые лабораторные запуски

- [Этап v0.4.5](experiments/v0_4_5.md).
- [Воспроизводимость](research/laboratory-run-reproducibility.md).
- [Сопоставимость и сравнение](research/laboratory-run-comparison.md).
- [Управление версиями кандидатов](research/candidate-version-governance.md).
- [Повтор запуска](getting-started/running-laboratory-replays.md).
- [Сравнение запусков](getting-started/comparing-laboratory-runs.md).

## Предложения лабораторных кандидатов

- [Этап v0.4.6](experiments/v0_4_6.md).
- [Этап v0.4.7](experiments/v0_4_7.md).
- [Слепая лабораторная проверка](research/blind-laboratory-validation.md).
- [Выполнение слепой проверки](getting-started/running-blind-laboratory-validation.md).
- [Управление предложением кандидата](research/candidate-proposal-governance.md).
- [Происхождение данных](research/training-data-lineage.md).
- [Воспроизводимость обучения](research/model-training-reproducibility.md).
- [предварительная внутренняя проверка](research/internal-screening-policy.md).
- [Подготовка предложение кандидата](getting-started/preparing-candidate-proposals.md).
- [Ручное рассмотрение](getting-started/reviewing-candidate-proposals.md).
