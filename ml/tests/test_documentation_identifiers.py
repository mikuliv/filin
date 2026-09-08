from pathlib import Path

from tools.docs.validate_documentation_identifiers import find_in_text, validate


ROOT = Path(__file__).resolve().parents[2]


def test_corrupted_identifier_is_rejected():
    text = "Ошибочные формы: `phase1_среда выполнения_contract`, `blind_internal_контрольную`, `production_готов`, `validate-среда выполнения-package`."
    findings = find_in_text(text)
    assert {item.literal for item in findings} == {
        "phase1_среда выполнения_contract",
        "blind_internal_контрольную",
        "production_готов",
        "validate-среда выполнения-package",
    }


def test_valid_identifiers_and_russian_prose_are_accepted():
    text = "Русское описание рядом с `phase1_runtime_contract.json` и `production_ready`."
    assert find_in_text(text) == []


def test_current_documentation_has_no_cyrillic_identifiers():
    assert validate(ROOT) == []
