# Этап обучения v0.3.4

`run_v0_3_4_stage.py` сначала проводит шесть preflight-проверок. Полный запуск
требует policy, report и artifact paths; до этого он выполняет лишь безопасную
проверку конфигурации. Training состоит из 12 runs, internal validation — из
6 иных runs. v0.3.3 запрещён data-access policy.

Selection использует `StratifiedGroupKFold` только по `run_id`. Candidate
замораживается до загрузки validation; validation делает исключительно predict.
