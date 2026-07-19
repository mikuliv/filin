# Ограничения

## v0.3.6

Prospective holdout показал benign recall `0.625`, FPR `0.375` и macro F1 `0.730381`. Даже успешный
лабораторный holdout не означал бы production readiness; запрещены shadow mode, backend integration,
active response и автоматическое блокирование.

v0.3.3 подтвердил: frozen `network_sensor_v0_3` baseline имеет benign recall
`0.000` и false positive rate `1.000` на сложном external benign-трафике.
Backend integration до нового training campaign запрещена.

- лабораторная топология, ограниченный набор сервисов и классов;
- controlled scenarios вместо реального корпоративного background;
- отсутствие анализа encrypted traffic beyond доступных metadata;
- отсутствует проверка на другой физической инфраструктуре и длительный production monitoring;
- отсутствуют backend integration, online inference, сертификация и подтверждение для КИИ или ГИС;
- малый support и одинаковые метрики robustness-runs требуют осторожной интерпретации;
- отсутствует feature fusion и проверка на широком наборе сетевых сред.

`robustness_passed=true` означает прохождение заранее заданной лабораторной policy, а не промышленную готовность. Полученные результаты относятся к контролируемому лабораторному стенду и не подтверждают готовность модели к эксплуатации в производственной инфраструктуре.

Для v0.3.4 internal validation не является будущим полностью слепым final test:
постановка этапа использовала выводы v0.3.3. Нужен новый заранее зафиксированный
blind holdout; до него backend integration и online inference не выполняются.

## Ограничения v0.3.7

OOD означает недостаток знания, а не атаку. `insufficient_evidence` не считается правильным benign и не используется для маскировки false positives. Контекст строится только из наблюдаемого сетевого workflow; будущие окна, labels, execution metadata и identity-поля не являются features. Лабораторная internal validation не даёт разрешения на backend integration, response actions, shadow mode или deployment.

## Ограничения исторических формул v0.3.7

Следующие имена профиля `network_sensor_v0_5` не соответствуют буквальной
математической семантике, которую можно предположить по названию. Их значения и
исторические метрики не пересчитываются:

- `destination_set_jaccard_change` — ограниченная единицей абсолютная разность
  `unique_destinations_per_flow`, а не Jaccard distance множеств назначений;
- `http_response_status_entropy` — доля непустых групп 2xx/4xx/5xx, а не entropy
  распределения HTTP statuses;
- `consecutive_high_failure_windows` — сумма всех high-failure окон в доступной
  истории плюс текущее, а не длина непрерывной серии;
- `consecutive_high_flow_windows` — число исторических окон выше медианы плюс
  единица, а не длина непрерывной серии;
- `failed_then_successful_connection_rate` — минимум числа успешных и неуспешных
  соединений, делённый на `flow_count`; порядок «failed then successful» не
  устанавливается.

Эти признаки допустимы только как документированные исторические значения.
Будущий цикл обязан использовать новый semantic version и не должен выдавать
их за исправленные формулы.

Для будущей замены нужны: реальный Jaccard по сохранённым destination sets;
Shannon entropy по распределению status codes; trailing run length со сбросом
для обоих `consecutive_*`; последовательность connection outcomes для
`failed_then_successful_connection_rate`. Если необходимые source events не
сохраняются в feature builder, признак должен быть удалён или честно переименован,
а не вычисляться из несоответствующего surrogate. Затронутый исторический этап —
v0.3.7; ретроспективное исправление запрещено.

## Ограничения v0.3.8

Результат получен на controlled Docker lab, шести validation runs и 72 episodes; это внутренняя, а не перспективная или production validation. Несмотря на FPR `0` и высокий closed-set macro F1, система пропустила два attack episodes, attack-window alert recall составил только `0.60`, а 40% attack windows ушли в `review_required:weak_evidence`. Class-conditional support сильно перекрывается: support-conflict rate `0.981481`, поэтому наличие support нельзя трактовать как надёжную идентификацию класса. Очень большие thresholds отражают неоднородный масштаб лабораторных признаков. Validation запрещено использовать для fit, calibration, threshold tuning или повторной оценки после изменений.

## Ограничения v0.3.9

Episode-first promotion проверяется только на новых controlled Docker scenarios. Review не является benign и не является alert. Continuous support margin выражает относительную близость, а не доказательство класса; высокий binary support conflict сохраняется как диагностика и больше не используется как gate. Internal validation, даже положительная, не разрешает backend integration, shadow mode или production deployment и не заменяет новую prospective holdout.

Фактическая frozen validation отрицательна: 41.67% окон потребовали review,
attack episode recall равен 0.70, девять из 30 attack episodes не получили
active alert, а true-class support вошёл в top-2 только для 60.71% окон.
Высокий closed-set macro F1 не компенсирует этот operational failure. Нельзя
подбирать thresholds, support или lifecycle по этим 252 validation rows.

Первичный pre-prediction lock зафиксировал dataset, order, mapping и frozen
features, но из-за ошибочного пути сохранил пустые списки `capture_hashes`.
После prediction в manifest добавлены hashes 288 уже существовавших PCAP;
prediction не повторялась и данные не менялись. Audit сохраняет оба SHA-256 и
флаг `capture_evidence_completed_after_prediction=true`. Поэтому доказательство
порядка для PCAP-hash evidence слабее, чем для dataset/feature lock.
# Ограничения v0.3.10

Internal validation остаётся контролируемым локальным экспериментом и сама по себе не разрешает shadow mode. Старые v0.3.6–v0.3.9 datasets не используются для fit или tuning; после успешной policy они могут быть открыты только неизменному candidate на отдельном regression-этапе v0.3.11. Полностью новая prospective holdout всё равно потребуется после regression.

Pending и review не считаются правильным benign. Diagnostic support не является доказательством novelty и не участвует в pass/fail policy.

Фактическая internal validation показала идеальные closed-set и episode
метрики, но `120` из `180` attack windows после первого однократного alert
оказались в pending из-за causal deduplication: overall pending rate
`0.370370`, attack pending rate `0.666667`. Frozen policy трактует эти значения
как failure, хотя все 60 attack episodes обнаружены первым окном. Изменять
определение метрики, TTL или thresholds по validation запрещено. Continuous
support остаётся несогласованным с HGB: top-1 `0.311728`, top-2 `0.663580`,
binary conflict `0.941358`; поэтому он остаётся только диагностическим.
# Ограничения аудита v0.3.10.1

Диагностическая переклассификация не является новой validation и не разрешает post-hoc изменение thresholds. Deduplicated continuation уже обнаруженного эпизода не означает analyst review или пропущенную детекцию. RTX 5060 Ti не используется frozen HGB/NumPy/Python pipeline; GPU-смена требует нового научного протокола.

# Ограничения v0.3.11

Положительная внутренняя validation v0.3.11 относится только к synthetic traffic контролируемого Docker-стенда. Она не является blind holdout, production validation или доказательством переносимости. Policy evaluator на короткой 12-policy проверке дал speedup 1,23× вместо инженерной цели 4×; CPU average/median targets также не пройдены. Из-за Windows/Docker race пять validation runs пришлось безопасно возобновить с одним Docker worker. Эти ограничения не меняют probabilities или scientific pass/fail, но требуют v0.3.12 regression и последующей v0.3.13 blind holdout до обсуждения shadow mode.
# Ограничения regression v0.3.12

v0.3.12 не подтверждает переносимость на все исторические условия: три из пяти benchmark нельзя было оценить без нарушения frozen-data contract. Положительные результаты v0.3.9/v0.3.10 не компенсируют отсутствие coverage; readiness к blind holdout, shadow mode и backend integration остаётся отрицательной.

# Ограничения аудита v0.3.12.1

Аудит использует только frozen records и не предлагает thresholds по историческим строкам. Исправленная causal интерпретация latency не является пересчётом официального gate. Rebuildable PCAP/Zeek источники v0.3.6/v0.3.7 не эквивалентны отсутствующей frozen feature table.
