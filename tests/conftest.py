"""Shared test fixtures: keep the real environment clean of Forage config."""

import json
from pathlib import Path

import pytest

from forage.config import GITHUB_TOKEN_ENV, LLM_API_KEY_ENV

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def clean_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with neither env var set unless it sets its own."""
    monkeypatch.delenv(GITHUB_TOKEN_ENV, raising=False)
    monkeypatch.delenv(LLM_API_KEY_ENV, raising=False)


@pytest.fixture
def invoice_search_payload() -> dict:
    """Recorded GitHub /search/repositories response (seam 1 fixture).

    Contains 6 good repos plus archived / BUSL-1.1 / unlicensed /
    NOASSERTION decoys that out-star every good repo — if the hard filters
    regressed, the decoys would rank top and the assertions would fail.
    """
    path = FIXTURES_DIR / "search_invoice_maker.json"
    return json.loads(path.read_text(encoding="utf-8"))
