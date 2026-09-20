from scripts.validate import validation_commands


def test_validation_commands_share_one_ordered_gate() -> None:
    commands = validation_commands(include_docker=False)
    rendered = [" ".join(command) for command in commands]

    assert "pip check" in rendered[0]
    assert "ruff check ." in rendered[1]
    assert "ruff format --check ." in rendered[2]
    assert "pytest -q" in rendered[3]
    assert rendered[4].endswith("-m build")


def test_docker_is_optional_and_last() -> None:
    commands = validation_commands(include_docker=True)

    assert commands[-1] == ["docker", "build", "-t", "gemma-jev:validation", "."]
