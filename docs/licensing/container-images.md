# Контейнерные ссылки

Инвентаризируются все `FROM`, Compose `image:`, apt install-команды и GitHub Actions refs. Docker daemon опрашивается только через локальный `docker image ls`; `pull` не выполняется. Отсутствующий образ получает статус `not_available_offline`, но не `verified`.

Mutable references сохраняются как findings. Исторические frozen-файлы не исправляются; вместо этого они исключаются из распространяемого bundle. Машинный реестр: `container-images.json`.

