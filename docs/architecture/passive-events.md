# Пассивные события

Passive event — versioned, проверяемое сообщение о результате анализа. Оно
содержит candidate identity, runtime reference, causal order, prediction link и
пассивный payload, но не содержит команды воздействия.

Current candidate совместим с `shadow_event_v2`. Event validation выполняется
до durable commit. Semantic duplicate означает повторное логическое событие;
transport duplicate означает повторную попытку доставки того же события.

Даже корректное passive event не разрешает shadow mode, backend integration,
notification или blocking.
