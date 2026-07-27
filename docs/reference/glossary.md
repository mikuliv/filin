---
doc_schema: filin_document_v2
title: Глоссарий
document_type: reference
audience:
  - newcomer
  - developer
  - operator
  - auditor
lifecycle: current
authoritative_for:
  - project_glossary
source_of_truth:
  - versioned_contracts
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Глоссарий

## Данные

- **сетевое наблюдение** — доступная в момент обработки запись о сетевом обмене;
- **пассивное событие** (`passive event`, `shadow_event_v2`) — versioned сообщение
  о model/runtime результате без автоматического действия;
- **подтверждающий материал** (`evidence reference`) — проверяемая ссылка на исходный artifact;
- **комплект подтверждающих материалов** (`evidence bundle`) — связанный manifest набор artifacts.

## Модель

- **причинный признак** — feature, допустимый по времени принятия решения;
- **зафиксированный кандидат** (`frozen candidate`) — неизменяемая связка model artifact,
  preprocessing, calibration, conformal и state policy;
- **эпизод** — группа связанных rows, для которой принимается одно решение;
- **отказ от решения** (`abstention`) — сохранение неопределённости вместо forced label.

## Оценка

- **контрольная выборка** (`holdout`) — данные, не использованные для подбора кандидата;
- **политика результата** (`policy result`) — machine-readable итог frozen gates;
- **тестовый оракул** (`test oracle`) — ожидаемая структура/метка только для test layer;
- **область подтверждения** (`confirmed scope`) — точные условия, в которых claim поддержан.

## Runtime

- **локальный staging transport** — изолированный путь доставки passive event;
- **эталонный приёмник** (`reference receiver`) — проверяемый локальный consumer, не production backend;
- **операционный overlay** — изменяемая база review поверх read-only source artifacts.

## Реконструкция

- **наблюдаемый факт** (`observable fact`) — утверждение, прямо связанное с evidence;
- **временное отношение** (`temporal relation`) — порядок/интервал с precision и uncertainty;
- **структурное отношение** (`structural relation`) — проверяемая некаузальная связь объектов;
- **разрыв реконструкции** (`reconstruction gap`) — явно представленное отсутствие нужных сведений;
- **группа корреляции** (`correlation group`) — группа объектов по versioned rule, не causal chain;
- **карточка v2** (`incident_card_v2`) — агрегированное лабораторное представление reconstruction.

## Гипотезы

- **гипотеза** (`hypothesis`) — конкурирующее объяснение, не установленный факт;
- **профиль обоснованности** (`evidential profile`) — supporting, contradicting и missing assessments;
- **сопоставление гипотез** (`hypothesis comparison`) — row-versus-column результат без ranking truth;
- **равная опора** (`equally_supported`) — evidence не даёт одной гипотезе преимущество.

## Консоль

- **лабораторный случай** (`laboratory case`) — синтетический versioned bundle для UI/workflow проверки;
- **ручное рассмотрение** (`manual review`) — operator states, notes и decision в отдельном overlay;
- **операторский цикл** (`operator workflow`) — последовательность от каталога до export.

## Внешняя проверка

- **независимая экспертная проверка** (`independent review`) — проверка package внешней ролью;
- **слепое независимое испытание** (`blind trial`) — будущая процедура с разделением data/labels/results;
- **план испытания** (`trial plan`) — согласованная до запуска спецификация, не разрешение само по себе.

## Целостность

- **SHA-256** — digest байтов artifact;
- **семантический SHA** (`semantic SHA`) — digest нормализованного значимого содержимого;
- **предварительная криптографическая фиксация** (`commitment`) — digest, опубликованный до раскрытия;
- **отсоединённая контрольная сумма** (`detached SHA`) — отдельный файл identity manifest.

## Статусы

- **текущий** (`current`) — применим к текущей архитектуре;
- **исторический** (`historical`) — сохраняет прежний результат или устройство;
- **замороженный** (`frozen`) — байты защищены manifest/protocol;
- **перенаправление** (`redirect`) — compatibility path без собственной авторитетности.
