# Пассивные события

Passive event — версионированный, проверяемое сообщение о результате анализа. Оно
содержит candidate identity, среда выполнения reference, causal order, prediction link и
пассивный payload, но не содержит команды воздействия.

текущий candidate совместим с `shadow_event_v2`. Event проверка выполняется
до durable Коммит. Semantic duplicate означает повторное логическое событие;
transport duplicate означает повторную попытку доставки того же события.

Даже корректное passive event не разрешает пассивное наблюдение, подключение к серверной части,
notification или blocking.
