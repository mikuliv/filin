# Филин v0.3.6 — prospective holdout

Это перспективная holdout-проверка, независимая от обучения и выбора модели, но не double-blind.
Frozen candidate v0.3.4 был зафиксирован до protocol. Фаза A запрещает загрузку artifact и predict;
фаза B собирает 12 Docker-runs и блокирует 252 строки; фаза C выполняет predict один раз.

Macro F1 `0.730381`, balanced accuracy `0.881944`, benign recall `0.625`, FPR `0.375`, attack macro
recall `0.933333`, collapsed attack precision `0.454545`, collapsed attack recall `1.0`. Policy не
пройдена. `candidate_ready_for_shadow_mode=false`, `model_refit_on_v036=false`,
`sensor_ready_for_backend_integration=false`. Candidate и threshold после evaluation не изменялись.

`--resume` воспроизводит post-hoc reports из immutable predictions; повторный predict, metric-driven
rerun и использование holdout для model selection блокируются.
