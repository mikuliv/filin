# Аудит происхождения файлов

Для 100% tracked-файлов фиксируются SHA-256, первый commit, дата и исходная Author identity по полной истории refs. Переименования учитываются через rename records. Отсутствие первого появления блокирует строгую проверку кодом `file_provenance_missing`.

Машинный результат: `file-provenance-audit.json`.

