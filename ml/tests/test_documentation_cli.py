from pathlib import Path

from tools.docs.validate_documentation_cli import available_commands, find_unknown_commands, validate


ROOT = Path(__file__).resolve().parents[2]


def test_documented_cli_commands_are_current():
    assert not validate(ROOT)
    reference = (ROOT / "docs/reference/command-reference.md").read_text(encoding="utf-8")
    for command in available_commands():
        assert f"| `{command}` |" in reference


def test_unknown_cli_command_is_rejected():
    text = "python -m lab.network_validation.cli definitely-nonexistent-command"
    assert find_unknown_commands(text, available_commands()) == ["definitely-nonexistent-command"]
    assert find_unknown_commands("| `definitely-nonexistent-command` | Ошибка |", available_commands())


def test_real_cli_commands_are_accepted():
    text = "python -m lab.network_validation.cli validate-config\npython -m lab.network_validation.cli inspect-run-plan"
    assert find_unknown_commands(text, available_commands()) == []
