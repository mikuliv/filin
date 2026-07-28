# Воспроизводимость обучения v0.4.6

Safe runner выполняет только встроенный allowlist recipe `hgb-multiclass-v046-r1` внутри процесса Python. Сеть, shell, произвольные модули, команды, пути, AutoML и подбор параметров запрещены.

Каждое выполнение имеет уникальный execution ID и детерминированный training semantic ID. Сравниваются параметры, порядок признаков, классы, прогнозы, byte SHA и model semantic fingerprint. Незавершённый binary не принимается; после перезапуска оператор явно архивирует частичный результат или повторяет frozen execution.

Модельный binary остаётся в `runtime/lab_console/v0_4_6/` и не включается в Git или export. Evidence содержит только безопасные manifest/fingerprint сведения.
