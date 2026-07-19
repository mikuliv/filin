# Дорожная карта

Машиночитаемым авторитетным источником текущего статуса является
[`research-state.yaml`](research-state.yaml).

## Завершённые исследовательские этапы

- v0.3.1 — базовая оценка.
- v0.3.2 — проверка устойчивости зафиксированной модели.
- v0.3.3 — отрицательная оценка в изменённой среде: benign recall `0.000` и
  false positive rate `1.000` в рамках исторического протокола.
- v0.3.4 — переработка benign-представления, групповая внутренняя валидация и
  заморозка кандидата.
- v0.3.5 — frozen regression evaluation на известном историческом benchmark;
  это не слепой перспективный holdout.
- v0.3.6 — перспективный holdout завершён, политика не пройдена; исторический
  результат неизменяем и не может повторно использоваться для настройки.
- v0.3.7 — новый иерархический цикл обучения и внутренней валидации завершён;
  зафиксированная политика внутренней валидации не пройдена.
- v0.3.8 — class-conditional uncertainty, conformal/support evidence и
  episode-level decision проверены на новых 12+6 runs; policy не пройдена.
- v0.3.9 — episode-first promotion, signed evidence и lifecycle проверены на
  новых 12+6 runs; policy не пройдена.
- v0.3.12 — frozen multi-benchmark regression завершена без fit; evaluation coverage и episode gate не пройдены.

## Активная работа

Активный эксперимент отсутствует. v0.3.12 завершён с отрицательным regression-решением; frozen candidate v0.3.11 не изменён.

## Следующий допустимый этап

Следующий допустимый вид работ — новый training cycle с новыми данными, runs и заранее зарегистрированной политикой. v0.3.13 blind holdout, shadow mode и backend integration запрещены, поскольку `candidate_ready_for_v0_3_13_blind_holdout=false`.

Последующий перспективный holdout потребует отдельно зарегистрированного
протокола, ранее не использовавшихся сценариев и единственного predict после
заморозки кандидата и политики. Интеграция с backend и теневой режим остаются
запрещены до явного прохождения применимой будущей политики. Готовность к
промышленной эксплуатации не подтверждена.

## Долгосрочные направления

Валидация на независимой инфраструктуре, наблюдаемость шифрованного трафика,
online inference, рабочее место аналитика, интеграция с SIEM и response actions
остаются будущими исследовательскими направлениями. Active response и
автоматическая блокировка не входят в текущий объём работ.
# После v0.3.10

Если frozen policy v0.3.10 пройдена, следующий этап — v0.3.11 frozen multi-benchmark regression без fit, calibration или изменения decision policy. После успешной regression потребуется v0.3.12 prospective holdout. Shadow mode можно рассматривать только после успешной v0.3.12.

Если policy v0.3.10 не пройдена, старые benchmarks не открываются для tuning: фиксируется отрицательный результат и проектируется новый training cycle.

Фактическая ветвь — отрицательная: при episode recall `1.0` frozen
pending/review gate не пройден (`pending_rate=0.370370`,
`attack_pending_rate=0.666667`), а training-only model-selection policy также
не пройдена. Поэтому v0.3.11 не открыта; разрешено только проектирование нового
training cycle на новых данных с заранее зафиксированным протоколом.
# После аудита v0.3.10.1

Следующий научный цикл должен заранее заморозить раздельные состояния и gates для pre-alert pending, post-alert continuation, duplicate suppression и unresolved pending. Validation v0.3.10 нельзя использовать для tuning; оно может стать regression benchmark только после независимого выбора нового candidate.

# После v0.3.11

Burden-aware internal validation пройдена. Следующий разрешённый этап — v0.3.12 frozen multi-benchmark regression на неизменённых benchmarks v0.3.6–v0.3.10 без fit, calibration, tuning и изменения policy. После успешной regression потребуется новая prospective blind holdout v0.3.13. Shadow mode и backend integration до неё запрещены.
