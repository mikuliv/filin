# Проверка документации

Изменение документации должно пройти:

1. Markdown structure и internal link validation.
2. Status consistency.
3. Absolute path, privacy и secret checks.
4. Artifact exclusion и current bundle validation.
5. Полный regression suite.
6. `git diff --check`.

Historical evidence не форматируется и не переписывается ради style
consistency. Если validator обнаруживает conflict в immutable artifact,
исправление оформляется отдельным errata или compatibility rule с явным scope.

Команды приведены в [руководстве по тестированию](../getting-started/testing.md).
