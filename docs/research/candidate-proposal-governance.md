# Управление предложениями лабораторных кандидатов

`proposal_id` и `candidate_id` принадлежат разным пространствам идентичности. Предложение v0.4.6 существует только в локальном proposal catalog и не может быть зарегистрировано, активировано, продвинуто или автоматически выбрано.

Допустимый жизненный цикл: `draft` → проверка происхождения и leakage → реальные воспроизводимые обучения → frozen proposal → internal screening → сравнение с действующим кандидатом → заранее объявленный admission gate → сохраняемое ручное review → `admitted_to_separate_validation` либо `rejected`.

Admission означает только право подготовить отдельный будущий протокол. Candidate registry, active artifact, backend и frozen evidence предыдущих этапов остаются неизменными. API намеренно не содержит upload, arbitrary command, register, activate, promote или replace-active операций.
