# Decision layer

В v0.3.12.2 state machine оценивается исключительно в frozen causal order внутри `(benchmark, run, activity)`. Физический порядок JSON запрещён как источник episode latency и допускается только в явно помеченном legacy control, который не влияет на policy.

Decision layer получает только результаты уже выполненного model prediction. Closed-set class, conformal singleton и support по отдельности не являются alert.

В v0.3.9 strong согласованный attack evidence может активировать alert в первом окне. Weak evidence создаёт `pending:<class>` и требует повторения либо достижения signed threshold. Novel/ambiguous evidence ведёт в review только при отсутствии active alert. Review не считается правильным benign и не считается alert.

Lifecycle причинный, не использует labels или `episode_id`, сбрасывается между runs и по inactivity TTL. Hysteresis удерживает alert минимум два scored окна и не позволяет одному benign-окну мгновенно отменить активное состояние.
# Minimal promotion v0.3.10

Strong path требует attack top class, conformal singleton, frozen probability/margin thresholds и benign ceiling. Weak path создаёт pending и подтверждается `two_consecutive` либо `two_of_three`, выбранной только на training. Strong benign evidence сбрасывает pending. Ambiguous и novel направляются в review без автоматического analyst review для одиночного pending.

Alert — однократное immutable событие. Frozen dedup TTL подавляет повтор того же класса в одной causal activity sequence. Support, signed summation, decay, hysteresis и persistence не участвуют в решении.

Выбран global strong threshold `0.7`, margin `0.1`, benign ceiling `0.2`; weak
threshold `0.35`, repetition `two_consecutive`, pending TTL `2`, ambiguity
margin `0.03`, dedup TTL `3`. Frozen validation обнаружила 60/60 attack
episodes первым окном и подавила 120 повторных emissions. Pending-rate gate не
пройден; policy после validation не менялась.
# Семантическое уточнение v0.3.10.1

Для будущего цикла различаются `pre_alert_pending`, `alert_emitted`, `post_alert_continuation`, `duplicate_alert_suppressed`, `review_required` и `unresolved_pending`. Post-alert continuation не входит в pending burden, а deduplication не является analyst review. Frozen реализация v0.3.10 не изменена.

# Burden-aware promotion v0.3.11

Семантика `burden_aware_v1` причинно разделяет benign, pre-alert pending, alert emission, post-alert continuation и review states. Первый alert не подавляется, continuation относится к prior alert, dedup key ограничен run/activity/class и TTL=3, unresolved pending вычисляется только post-hoc. Frozen validation прошла все pending, review, dedup, episode, group, class и variant gates.
# Regression semantics v0.3.12

Frozen `burden_aware_v1` применена без изменения thresholds. На v0.3.9 получено 30 alert events и 59 post-alert continuations, на v0.3.10 — 60 и 120; continuation не считается pending или analyst burden. False duplicate suppression равна нулю. Detection by second window `0.733333` на обоих наборах ниже frozen gate `0.75`.

# Причинное уточнение v0.3.12.1

Immutable prediction хранит правильные `causal_order` и state transitions, но порядок элементов `records` не является causal. Поэтому episode latency нельзя вычислять через позицию элемента без сортировки. В causal order первый alert не подавляется, eligibility и emission совпадают, а дополнительная задержка state machine равна нулю. Frozen report и pass/fail не переписываются.
