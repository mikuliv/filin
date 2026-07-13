# v0.3.5 — frozen regression evaluation

Этап выполняет только offline predict frozen candidate v0.3.4 и reconstructed
baseline v0.3.1 на неизменяемом benchmark v0.3.3. Benchmark не участвует в
fit, model selection, preprocessing, настройке порогов или гиперпараметров.
Он не является полностью слепым final test, потому что его результаты были
известны при проектировании v0.3.4. Backend integration не выполняется.
