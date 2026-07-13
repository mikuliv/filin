# Ограничения

## v0.3.6

Prospective holdout показал benign recall `0.625`, FPR `0.375` и macro F1 `0.730381`. Даже успешный
лабораторный holdout не означал бы production readiness; запрещены shadow mode, backend integration,
active response и автоматическое блокирование.

v0.3.3 подтвердил: frozen `network_sensor_v0_3` baseline имеет benign recall
`0.000` и false positive rate `1.000` на сложном external benign-трафике.
Backend integration до нового training campaign запрещена.

- лабораторная топология, ограниченный набор сервисов и классов;
- controlled scenarios вместо реального корпоративного background;
- отсутствие анализа encrypted traffic beyond доступных metadata;
- отсутствует проверка на другой физической инфраструктуре и длительный production monitoring;
- отсутствуют backend integration, online inference, сертификация и подтверждение для КИИ или ГИС;
- малый support и одинаковые метрики robustness-runs требуют осторожной интерпретации;
- отсутствует feature fusion и проверка на широком наборе сетевых сред.

`robustness_passed=true` означает прохождение заранее заданной лабораторной policy, а не промышленную готовность. Полученные результаты относятся к контролируемому лабораторному стенду и не подтверждают готовность модели к эксплуатации в производственной инфраструктуре.

Для v0.3.4 internal validation не является будущим полностью слепым final test:
постановка этапа использовала выводы v0.3.3. Нужен новый заранее зафиксированный
blind holdout; до него backend integration и online inference не выполняются.

## Ограничения v0.3.7

OOD означает недостаток знания, а не атаку. `insufficient_evidence` не считается правильным benign и не используется для маскировки false positives. Контекст строится только из наблюдаемого сетевого workflow; будущие окна, labels, execution metadata и identity-поля не являются features. Лабораторная internal validation не даёт разрешения на backend integration, response actions, shadow mode или deployment.
