"""Unit tests for environment-only configuration (fail-fast behavior)."""

import pytest

from forage.config import (
    GITHUB_TOKEN_ENV,
    LLM_API_KEY_ENV,
    ConfigError,
    Settings,
    load_settings,
    missing_env_vars,
)


def test_missing_env_vars_when_environ_empty() -> None:
    assert missing_env_vars({}) == [GITHUB_TOKEN_ENV, LLM_API_KEY_ENV]


def test_missing_env_vars_treats_blank_as_missing() -> None:
    env = {GITHUB_TOKEN_ENV: "   ", LLM_API_KEY_ENV: "sk-ant-key"}
    assert missing_env_vars(env) == [GITHUB_TOKEN_ENV]


def test_missing_env_vars_when_only_llm_key_set() -> None:
    env = {LLM_API_KEY_ENV: "sk-ant-key"}
    assert missing_env_vars(env) == [GITHUB_TOKEN_ENV]


def test_missing_env_vars_none_when_both_set() -> None:
    env = {GITHUB_TOKEN_ENV: "github_pat_x", LLM_API_KEY_ENV: "sk-ant-key"}
    assert missing_env_vars(env) == []


def test_load_settings_raises_config_error_listing_missing() -> None:
    with pytest.raises(ConfigError) as exc_info:
        load_settings({})
    assert exc_info.value.missing == [GITHUB_TOKEN_ENV, LLM_API_KEY_ENV]
    assert GITHUB_TOKEN_ENV in str(exc_info.value)


def test_load_settings_returns_stripped_values() -> None:
    env = {GITHUB_TOKEN_ENV: "  github_pat_x  ", LLM_API_KEY_ENV: " sk-ant-key "}
    settings = load_settings(env)
    assert isinstance(settings, Settings)
    assert settings.github_token == "github_pat_x"
    assert settings.llm_api_key == "sk-ant-key"
