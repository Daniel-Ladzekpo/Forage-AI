"""CLI smoke tests for the scaffold: help, fail-fast, and the setup wizard."""

from typer.testing import CliRunner

from forage import __version__
from forage.cli import app
from forage.config import GITHUB_TOKEN_ENV, LLM_API_KEY_ENV
from forage.discovery import GitHubAPIError, parse_search_results

runner = CliRunner()

# Fixture decoys (archived / non-OSI / unlicensed) that must never render.
DECOY_FULL_NAMES = (
    "old-times/legacy-invoice",
    "proprietary-corp/closed-invoice",
    "no-license/mystery-invoice",
    "weird-license/noassertion-invoice",
)


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


def _fake_github_client(payload: dict):
    """Drop-in replacement for forage.cli.GitHubSearchClient (no network)."""

    class FakeClient:
        def search(self, query: str):
            return parse_search_results(payload)

    return lambda **_: FakeClient()


def _set_valid_config(monkeypatch) -> None:
    monkeypatch.setenv(GITHUB_TOKEN_ENV, "github_pat_test")
    monkeypatch.setenv(LLM_API_KEY_ENV, "sk-ant-test")


def test_find_renders_3_to_5_candidate_cards_from_fixture(
    monkeypatch, invoice_search_payload
) -> None:
    _set_valid_config(monkeypatch)
    monkeypatch.setattr(
        "forage.cli.GitHubSearchClient", _fake_github_client(invoice_search_payload)
    )
    result = runner.invoke(app, ["find", "a free invoice maker"])
    assert result.exit_code == 0
    output = flatten(result.output)
    # 6 good repos in the fixture, capped at 5 cards — acceptance: 3-5 cards
    assert output.count("https://github.com/") == 5
    assert "a free invoice maker" in output
    # stars, license, maintenance in plain English (user story 3)
    assert "12,400 stars" in output
    assert "License: MIT" in output
    assert "Maintenance:" in output
    assert "last commit" in output
    # hard filters (user story 11): the decoys out-star every good repo,
    # so any regression in the filters would surface them here
    for decoy in DECOY_FULL_NAMES:
        assert decoy not in output


def test_find_with_fully_filtered_results_gives_guidance(
    monkeypatch, invoice_search_payload
) -> None:
    _set_valid_config(monkeypatch)
    decoys_only = {
        "items": [
            item
            for item in invoice_search_payload["items"]
            if item["full_name"] in DECOY_FULL_NAMES
        ]
    }
    monkeypatch.setattr(
        "forage.cli.GitHubSearchClient", _fake_github_client(decoys_only)
    )
    result = runner.invoke(app, ["find", "anything"])
    assert result.exit_code == 0
    output = flatten(result.output)
    assert "No trustworthy Candidates found" in output
    assert "try a broader description" in output


def test_find_reports_api_errors(monkeypatch) -> None:
    _set_valid_config(monkeypatch)

    class ExplodingClient:
        def __init__(self, **kwargs) -> None:
            pass

        def search(self, query: str):
            raise GitHubAPIError("rate limit reached — wait a minute")

    monkeypatch.setattr("forage.cli.GitHubSearchClient", ExplodingClient)
    result = runner.invoke(app, ["find", "anything"])
    assert result.exit_code == 1
    assert "Search failed" in flatten(result.output)
    assert "rate limit" in flatten(result.output)


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
