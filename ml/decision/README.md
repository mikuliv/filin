# Decision layer

Decision layer получает только результаты уже выполненного model prediction. Closed-set class, conformal singleton и support по отдельности не являются alert.

В v0.3.9 strong согласованный attack evidence может активировать alert в первом окне. Weak evidence создаёт `pending:<class>` и требует повторения либо достижения signed threshold. Novel/ambiguous evidence ведёт в review только при отсутствии active alert. Review не считается правильным benign и не считается alert.

Lifecycle причинный, не использует labels или `episode_id`, сбрасывается между runs и по inactivity TTL. Hysteresis удерживает alert минимум два scored окна и не позволяет одному benign-окну мгновенно отменить активное состояние.
