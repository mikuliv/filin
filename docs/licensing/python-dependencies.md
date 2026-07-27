# Python-зависимости

Объявления извлекаются из всех tracked `requirements*.txt`; локально установленные distributions и их транзитивное замыкание — через `importlib.metadata`. License-Expression, classifiers и license files рассматриваются как evidence; нормализация в SPDX фиксируется отдельно. Сеть и установка пакетов не используются.

Неизвестная или неоднозначная лицензия, необъявленный import, отсутствующий distribution и dependency без диапазона версий являются блокерами строгой проверки. Машинные реестры: `python-dependencies-declared.json` и `python-dependencies-resolved.json`.

