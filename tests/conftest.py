"""Shared test fixtures: keep the real environment clean of Forage config."""

import pytest

from forage.config import GITHUB_TOKEN_ENV, LLM_API_KEY_ENV


@pytest.fixture(autouse=True)
def clean_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with neither env var set unless it sets its own."""
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    monkeypatch.delenv(LLM_API_KEY_ENV, raising=False)
