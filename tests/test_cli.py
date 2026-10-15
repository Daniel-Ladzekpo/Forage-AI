"""CLI smoke tests for the scaffold: help, fail-fast, and the setup wizard."""

from typer.testing import CliRunner

from forage import __version__
from forage.cli import app
from forage.config import GITHUB_TOKEN_ENV, LLM_API_KEY_ENV

runner = CliRunner()


def flatten(text: str) -> str:
    """Collapse whitespace so assertions don't care about rich's line wraps."""
    return " ".join(text.split())


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = flatten(result.output)
    assert "setup" in output
    assert "find" in output
    assert "install" in output


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_find_fails_fast_when_no_env_vars() -> None:
    result = runner.invoke(app, ["find", "a free invoice maker"])
    assert result.exit_code == 1
    output = flatten(result.output)
    assert GITHUB_TOKEN_ENV in output
    assert LLM_API_KEY_ENV in output
    assert "forage setup" in output


def test_install_fails_fast_when_no_env_vars() -> None:
    result = runner.invoke(app, ["install", "2"])
    assert result.exit_code == 1
    output = flatten(result.output)
    assert GITHUB_TOKEN_ENV in output
    assert LLM_API_KEY_ENV in output
    assert "forage setup" in output


def test_find_fails_fast_when_only_llm_key_missing(monkeypatch) -> None:
    monkeypatch.setenv(GITHUB_TOKEN_ENV, "github_pat_test")
    result = runner.invoke(app, ["find", "a simple video trimmer"])
    assert result.exit_code == 1
    output = flatten(result.output)
    assert LLM_API_KEY_ENV in output
    assert GITHUB_TOKEN_ENV not in output
    assert "forage setup" in output


def test_find_fails_fast_when_only_github_token_missing(monkeypatch) -> None:
    monkeypatch.setenv(LLM_API_KEY_ENV, "sk-ant-test")
    result = runner.invoke(app, ["find", "a simple video trimmer"])
    assert result.exit_code == 1
    output = flatten(result.output)
    assert GITHUB_TOKEN_ENV in output
    assert LLM_API_KEY_ENV not in output
    assert "forage setup" in output


def test_setup_never_requires_config_and_prints_instructions() -> None:
    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    output = flatten(result.output)
    assert GITHUB_TOKEN_ENV in output
    assert LLM_API_KEY_ENV in output
    assert "fine-grained" in output
    assert "github.com/settings/personal-access-tokens" in output
    assert "console.anthropic.com" in output
    assert "setx" in output


def test_setup_works_even_with_env_vars_set(monkeypatch) -> None:
    monkeypatch.setenv(GITHUB_TOKEN_ENV, "github_pat_test")
    monkeypatch.setenv(LLM_API_KEY_ENV, "sk-ant-test")
    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    assert GITHUB_TOKEN_ENV in flatten(result.output)


def test_find_with_config_reports_not_implemented_yet(monkeypatch) -> None:
    monkeypatch.setenv(GITHUB_TOKEN_ENV, "github_pat_test")
    monkeypatch.setenv(LLM_API_KEY_ENV, "sk-ant-test")
    result = runner.invoke(app, ["find", "a simple offline video trimmer"])
    assert result.exit_code == 1
    assert "not implemented" in flatten(result.output)


def test_install_with_config_reports_not_implemented_yet(monkeypatch) -> None:
    monkeypatch.setenv(GITHUB_TOKEN_ENV, "github_pat_test")
    monkeypatch.setenv(LLM_API_KEY_ENV, "sk-ant-test")
    result = runner.invoke(app, ["install", "2"])
    assert result.exit_code == 1
    assert "not implemented" in flatten(result.output)


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    # typer's no_args_is_help prints full help and exits with usage code 2.
    assert result.exit_code == 2
    assert "Usage" in result.output
    assert "setup" in result.output
