# v0.3.4 — переработка benign representation

Этап определяет две независимые кампании, три заранее зафиксированных профиля
признаков и ограниченный selection только по training-runs. `v0.3.3` не
загружается ни для fit, ни для CV, выбора порога или признаков: это locked
regression benchmark для отдельного этапа v0.3.5, но не полностью слепой test.

Internal validation открывается только после manifest-backed freeze; после неё
настройка модели запрещена. Новый blind holdout потребуется отдельной кампанией.
Backend integration и online inference не входят в этап.
