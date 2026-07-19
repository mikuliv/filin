# Научный цикл v0.3.11

Каталог фиксирует новый независимый training/validation цикл burden-aware promotion. Модель использует неизменяемую HGB/HGB-архитектуру и 51 причинный признак профиля `network_sensor_v0_5_contextual_control`. Калибровка, Mondrian conformal и выбор policy выполняются только на grouped OOF строках двенадцати новых training runs.

Prospective validation из шести новых runs разрешается собирать только после выбора и заморозки кандидата. После capture lock и validation lock выполняется ровно одна immutable prediction внутри no-fit guard. Исторические научные строки v0.3.6–v0.3.10 и аннотации v0.3.10.1 не являются источником обучения, калибровки или настройки.

Полный возобновляемый запуск:

```powershell
python ml/experiments/v0_3_11/run_v0_3_11.py `
  --protocol ml/experiments/v0_3_11/protocol.yaml `
  --resource-profile ml/experiments/v0_3_11/resource_profile.yaml `
  --workers auto `
  --strict `
  --resume
```

Модели, datasets, PCAP, Zeek logs, predictions, resource traces и вычисляемые отчёты остаются runtime-артефактами вне Git. Даже при успешной внутренней validation интеграция с backend и shadow mode запрещены; следующий допустимый этап — frozen multi-benchmark regression v0.3.12 без fit, calibration и tuning.
