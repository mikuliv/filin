# Эксперимент v0.3.9

Новый training/internal-validation cycle проверяет episode-first alert promotion. Base HGB/HGB, 51-feature contextual profile, OOF sigmoid calibration и Mondrian `alpha=0.05` фиксированы до training. Широкий model/feature search запрещён.

Selection состоит из 8 strong-gate, 8 weak-evidence и не более 32 lifecycle candidates только на grouped training OOF. Frozen candidate создаётся до validation collection; validation lock — до единственной immutable prediction.

Primary detection metric — attack episode recall. Final attack-window alert rate диагностический: pre-alert окно не делает обнаруженный episode пропущенным. Binary support conflict не является gate; используются continuous normalized distances и margins. Runtime models, datasets, predictions и reports не коммитятся.
