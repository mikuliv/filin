# Условия среды v0.3.3

Этот каталог задаёт audit условий mixed, hard-negative, degraded и TLS/proxy runs. Конфигурация зависит только от группы и seed, а не от label. Audit metadata не являются модель features.

## Результат v0.3.3

На 144 benign windows Зафиксировано baseline дал benign Полнота `0.000`. Модель не
переобучалась на v0.3.3, policy не менялась после результата, а маркеры и
environment metadata не входят в модель features.
