# Линия текущего кандидата

## Идентичность

- Candidate ID: `v03154:65a3dd912d845bc1`.
- Artifact SHA-256: `65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87`.
- Feature contract: `network_features_v2`.
- Manifest: `ml/artifacts/v0_3_15_4/candidate_manifest.json`.
- Registry: `collectors/shadow/contracts/candidate_registry_v1.json`.

## Происхождение

Кандидат создан в контролируемой redevelopment campaign `v0.3.15.4`, прошёл
заранее зафиксированный prospective holdout `v0.3.15.5`, затем совместимый
runtime recovery `v0.3.15.5.1`. Последующие staging, rehearsal, external package
и `v0.4.x` не переобучали и не заменяли его.

## Ограничение статуса

Candidate promoted внутри локальной исследовательской линии, но внешняя validation
не завершена. Он не разрешён для production, real shadow mode или automatic action.

Machine-readable identity имеет приоритет над этой страницей. Проверяйте оба
источника и [основной status registry](../status/project-status.yaml).
