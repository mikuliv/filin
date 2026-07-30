# Протокол следующей независимой сетевой проверки

## Назначение

Протокол задаёт минимальную проверку внешней переносимости сетевого классификатора. Он не имеет номера стадии, ничего не запускает и не разрешает переобучение или замену кандидата.

## Независимость генераторов

1. Использовать не менее двух независимо реализованных семейств генерации: одно только для разработки, второе только для финального контроля.
2. Код финального генератора не импортирует и не вызывает packet/capture generator обучающего семейства.
3. Разбиение выполняется по generator family целиком, а не по seed, session suffix или отдельному файлу.
4. До раскрытия финальных меток сохранить хеши исходников, образов, конфигурации и параметрических распределений обоих семейств.

## Реальный сетевой путь

Основной PCAP должен быть результатом фактического обмена:

```text
scenario runner → Docker client → network → target service → sensor
→ PCAP → Zeek → 51 features
```

Непосредственно созданные библиотекой пакеты не входят в основной оценочный корпус. Для каждого запуска фиксируются execution ID, marker start/end, capture start/end, container/image digest, network identity, client/target timestamps, exit status, packet count, PCAP size и SHA-256. Marker traffic исключается из model input и проверяется отдельным тестом.

## Контроль client fingerprint

- Для benign и attack используются одинаковые client image, сетевой стек, исходный адресный пул, DNS policy и базовый набор заголовков.
- Отличия user-agent, connection reuse, TLS, retry policy и payload encoding не должны однозначно кодировать класс, если они не являются предметом проверяемой атаки.
- Для каждой пары классов проводится тест возможности предсказания label только по client/infrastructure metadata.

## Независимая инфраструктура

Финальный контроль отделяется по target instance, IP/port allocation, container image digest, DNS, server implementation и response templates. Минимум одна часть запускается в отдельной сети и на другом host/VDS. Дополнительно включается внешний опубликованный PCAP или Zeek corpus с совместимой разметкой, если его лицензия и feature mapping проверены заранее.

## Проверка реализации параметров

Для каждого параметра сохраняются `requested`, `observed`, `tolerance`, `passed` и ссылка на измерение в PCAP/Zeek:

- spacing;
- payload size;
- flow/request count;
- retry count и backoff;
- response order;
- timeout mode;
- background traffic level;
- scenario duration.

Значения `observed` извлекаются автоматической проверкой из PCAP и Zeek logs, а не переносятся из конфигурации сценария. Запуск не допускается в оценку, если заявленный параметр не проявился в наблюдаемом трафике либо расхождение превышает предварительно заданную tolerance.

## Контрфактические пары

Набор обязан включать пары, в которых меняется только один фактор:

- тот же client и target, benign ↔ attack behavior;
- тот же behavior, другой generator family;
- тот же behavior, другой target implementation;
- те же volume/timing, другой semantic outcome;
- тот же outcome, другие port/path/status/payload size;
- одинаковый сценарий с background traffic и без него;
- одинаковые параметры в начале, середине и конце сессии.

## Предварительно фиксируемые baselines и ablations

До финального holdout фиксируются реализации и параметры:

- majority;
- ports/services only;
- traffic intensity only;
- timing only;
- HTTP only;
- rolling/history only;
- suffix/session position only;
- logistic regression;
- nearest centroid;
- decision tree с заранее заданной глубиной;
- полный frozen candidate;
- ablation каждого семейства признаков, включая отдельное исключение предполагаемых proxy-признаков.

Prospective holdout не используется для выбора baseline-параметров, признаков, порогов или кандидата.

## Разбиение

Train, calibration, internal audit и final holdout не пересекаются по session, target instance, infrastructure campaign и generator family. Final holdout дополнительно содержит невиданные parameter combinations и контрфактические пары. Все правила назначения split и исключения фиксируются до создания финальных labels/predictions.

## Слепая фиксация

До раскрытия финальных меток фиксируются:

- feature schema и точный порядок столбцов;
- preprocessing и missing-value policy;
- model bytes и SHA-256;
- один окончательный внутренний и внешний ID, вычисленный после последней сериализации;
- class map, thresholds и calibration;
- метрики, episode rules, latency definition;
- exclusion rules и критерии принятия;
- хеши manifests, source tree и входных PCAP.

После раскрытия labels запрещены tuning, замена кандидата, изменение исключений и повторное объявление набора слепым.

## Окружение

Lock содержит Python, scikit-learn, joblib, Zeek version и image digest, Docker/Compose, OS, зависимости client/target, feature order и model serializer. Перед inference отдельно проверяются compatibility и integrity; недоверенная сериализация не загружается.

## Критерии принятия

Технические обязательные условия:

- 100% включённых запусков имеют полную цепочку и хеши;
- отсутствуют точные PCAP/feature duplicates между split;
- параметры подтверждены наблюдаемым трафиком;
- final generator и infrastructure не использовались при разработке;
- frozen predictions сопоставлены с labels один раз и независимо пересчитаны.

Научные критерии задаются до запуска и не копируют идеальные значения прежнего корпуса. Минимально оцениваются accuracy, macro-F1, per-class precision/recall/F1, FPR, FNR, episode recall, false alarms и latency с доверительными интервалами. Приемлемость требует устойчивости на обеих generator families, независимой инфраструктуре и контрфактических парах, а также существенного преимущества над простыми baselines. Любое семейство с неприемлемым worst-class recall приводит к ограниченному или отрицательному выводу, а не к усреднённому положительному статусу.

## Результат протокола

Документ определяет будущую проверку; эксперимент не выполнялся. До её завершения нельзя утверждать внешнюю валидность, практическую точность или production-готовность текущего кандидата.

## Состояние технической инфраструктуры

Реализация находится в `lab/network_validation` и включает общий client identity,
два независимо реализованных семейства сетевых действий, два target/network
профиля, capture sidecar, Zeek parameter verification, причинный адаптер 51
признаков, split/proxy validators, environment lock и freeze preview.

Техническая campaign-конфигурация проходит schema, counterfactual и split checks.
Она остаётся fixture: proxy-risk warnings не устранены, числовые критерии принятия
не утверждены, image digests не зафиксированы, поэтому seal невозможен. Docker
smoke и научный запуск не выполнялись; корпуса, labels, predictions и metrics не
создавались.
