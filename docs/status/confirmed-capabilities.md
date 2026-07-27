# Подтверждённые возможности

Каждая возможность ограничена этапом и областью проверки. Наличие строки не
означает внешнюю или промышленную готовность.

## Научные и модельные результаты

| capability_id | Возможность | Этап | Подтверждено | Не подтверждено | Evidence |
|---|---|---|---|---|---|
| `causal_feature_contract` | Причинное 51-признаковое представление | `v0.3.15.4` | Воспроизводимая форма входа `network_features_v2` | Переносимость на произвольную сеть | [отчёт](../../ml/reports/v0_3_15_4/v0_3_15_4_summary.md) |
| `frozen_inference` | Зафиксированный inference | `v0.3.15.4–v0.3.15.5.1` | Неизменяемые artifact, mapping, preprocessing и policies | Будущее качество на внешних данных | [manifest](../../ml/artifacts/v0_3_15_4/candidate_manifest.json) |
| `laboratory_class_recognition` | Распознавание предусмотренных классов | `v0.3.15.5` | Scientific gates frozen holdout в заданной области | Общая внешняя точность | [policy](../../ml/reports/v0_3_15_5/v0_3_15_5_policy_result.json) |
| `episode_decision` | Эпизодное решение и отказ от forced winner | `v0.3.15.5.1` | Детерминированная локальная политика | Истинность класса и реальное реагирование | [policy](../../ml/reports/v0_3_15_5_1/v0_3_15_5_1_policy_result.json) |

## Инженерный runtime основной линии

| capability_id | Возможность | Этап | Подтверждено | Не подтверждено | Evidence |
|---|---|---|---|---|---|
| `passive_event_v2` | Пассивное событие | `v0.3.15.5.1` | Candidate-compatible `shadow_event_v2` | Реальный shadow mode | [контракт](../contracts/shadow-event-v2.md) |
| `local_reliable_delivery` | Надёжная локальная доставка | `v0.3.16–v0.3.17.1` | Изолированный staging transport и проверяемый receiver | Production backend | [policy](../../ml/reports/v0_3_16/v0_3_16_policy_result.json) |
| `external_review_package` | Frozen комплект внешней процедуры | `v0.3.18` | Комплект, роли и синтетическая репетиция | Само внешнее испытание | [manifest](../../ml/reports/v0_3_18/external_review_package_manifest.yaml) |

## Лабораторная реконструкция v0.4

| capability_id | Возможность | Этап | Подтверждено | Не подтверждено | Evidence |
|---|---|---|---|---|---|
| `observable_facts` | Наблюдаемые факты из ссылок на evidence | `v0.4.0` | Детерминированная лабораторная проекция | Независимое криминалистическое заключение | [описание](../research/incident-reconstruction.md) |
| `temporal_reconstruction` | Временная реконструкция | `v0.4.1` | Порядок, интервалы и неопределённость | Причинная связь | [protocol](../../incident_reconstruction/protocols/v0_4_1_protocol_r2.yaml) |
| `structural_relations` | Структурные отношения и группы | `v0.4.2` | Проверяемые некаузальные связи | Действия злоумышленника | [protocol](../../incident_reconstruction/protocols/v0_4_2_protocol_r1.yaml) |
| `reconstruction_gaps` | Явные разрывы реконструкции | `v0.4.1–v0.4.4` | Недостающие сведения представлены отдельно от фактов | Автоматическое устранение разрыва | [ограничения](../../ml/reports/v0_4_4/known_limitations.md) |
| `competing_hypotheses` | Конкурирующие гипотезы | `v0.4.2` | Несколько объяснений и отсутствие forced winner | Истинность лучшей гипотезы | [описание](../research/competing-hypotheses.md) |
| `incident_card_v2` | Карточка v2 | `v0.4.3` | Детерминированная сборка лабораторной карточки | Заключение о компрометации | [контракты](../contracts/index.md) |

## Консоль и операторский цикл

| capability_id | Возможность | Этап | Подтверждено | Не подтверждено | Evidence |
|---|---|---|---|---|---|
| `local_console` | Локальная консоль | `v0.4.3` | localhost, token auth, read-only source data | Публичный сервис или SIEM | [описание](../architecture/laboratory-console.md) |
| `laboratory_case_catalog` | 12 независимых карточек | `v0.4.4` | Уникальные card ID и semantic SHA | Покрытие реальных инцидентов | [manifest](../../ml/reports/v0_4_4/v0_4_4_bundle_manifest.json) |
| `persistent_operator_cycle` | Сохраняемый операторский цикл | `v0.4.4` | SQLite overlay, progress, notes и decision | Разрешение автоматических действий | [policy](../../ml/reports/v0_4_4/v0_4_4_policy_result.json) |
| `manual_review_overlay` | Ручное рассмотрение без изменения evidence | `v0.4.4` | Source artifacts остаются read-only | Превращение заметки в evidence | [acceptance](../../ml/reports/v0_4_4/operator_acceptance_report.md) |
| `deterministic_review_export` | Детерминированный экспорт | `v0.4.4` | Повторяемый export одного состояния | Внешняя юридическая или научная валидность | [reproduction](../../ml/reports/v0_4_4/reproduction.md) |

## Общее ограничение

Все перечисленные возможности подтверждены только в своей лабораторной области.
Запреты собраны на [канонической странице](prohibited-capabilities.md).
