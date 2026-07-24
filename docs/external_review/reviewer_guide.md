# Руководство внешнего reviewer

1. Проверить detached hash package manifest.
2. Запустить standalone verifier из чистого каталога без Git и сети.
3. Сверить candidate, protocol и evaluator commitments.
4. Проверить role conflicts и chronology: label reveal должен следовать после
   prediction commitment.
5. Убедиться, что data usage mode единственный и согласован.
6. Проверить limitations, sample plan и unresolved acceptance thresholds.
7. Зафиксировать как положительные, так и отрицательные findings.

Reviewer не утверждает научный результат до реального blind trial.
