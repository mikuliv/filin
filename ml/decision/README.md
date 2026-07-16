# Decision layer

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
