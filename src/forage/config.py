"""Environment-only configuration for Forage.

Round-2 decisions Q4/Q5: secrets come exclusively from the
``FORAGE_GITHUB_TOKEN`` and ``FORAGE_LLM_API_KEY`` environment variables —
never hardcoded, no config files in v1, and no anonymous degraded mode:
when either variable is missing, every command (except ``forage setup``)
fails fast with guidance pointing at ``forage setup``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

GITHUB_TOKEN_ENV = "FORAGE_GITHUB_TOKEN"
LLM_API_KEY_ENV = "FORAGE_LLM_API_KEY"

REQUIRED_ENV_VARS: tuple[str, ...] = (GITHUB_TOKEN_ENV, LLM_API_KEY_ENV)


class ConfigError(Exception):
    """Raised when one or more required environment variables are missing."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )


class Settings(BaseModel):
    """The complete v1 configuration surface (env vars only)."""

    model_config = ConfigDict(frozen=True)

    github_token: str
    llm_api_key: str


def missing_env_vars(environ: Mapping[str, str] | None = None) -> list[str]:
    """Return the required env var names that are unset or blank."""
    env = os.environ if environ is None else environ
    return [name for name in REQUIRED_ENV_VARS if not env.get(name, "").strip()]


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Load settings from the environment, failing fast on anything missing."""
    env = os.environ if environ is None else environ
    missing = missing_env_vars(env)
    if missing:
        raise ConfigError(missing)
    return Settings(
        github_token=env[GITHUB_TOKEN_ENV].strip(),
        llm_api_key=env[LLM_API_KEY_ENV].strip(),
    )
