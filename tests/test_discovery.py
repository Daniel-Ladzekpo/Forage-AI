"""Seam 1: DiscoveryService.search(discoveryQuery) with a fake GitHub API.

All tests are hermetic — recorded JSON fixture or httpx.MockTransport,
never the live network.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from forage.discovery import (
    GitHubAPIError,
    GitHubSearchClient,
    DiscoveryService,
    format_license,
    format_stars,
    format_updated,
    hard_filter,
    maintenance_signal,
    parse_search_results,
)

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

# Fixture decoys that out-star every good repo; none may ever surface.
DECOY_FULL_NAMES = {
    "old-times/legacy-invoice",       # archived (15,000 stars)
    "proprietary-corp/closed-invoice",  # BUSL-1.1, non-OSI (13,000)
    "no-license/mystery-invoice",     # no license at all (11,000)
    "weird-license/noassertion-invoice",  # NOASSERTION (10,000)
}


class FakeGitHubSearch:
    """Recorded-fixture stand-in for GitHubSearchClient."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.queries: list[str] = []

    def search(self, query: str) -> list:
        self.queries.append(query)
        return parse_search_results(self._payload)


def test_parse_search_results_reads_recorded_fixture(invoice_search_payload) -> None:
    repos = parse_search_results(invoice_search_payload)
    assert len(repos) == 10
    by_name = {repo.full_name: repo for repo in repos}
    assert by_name["sharp-tools/invoice-sharp"].stars == 12400
    assert by_name["sharp-tools/invoice-sharp"].license_spdx == "MIT"
    assert by_name["old-times/legacy-invoice"].archived is True
    assert by_name["no-license/mystery-invoice"].license_spdx is None
    assert by_name["no-license/mystery-invoice"].description is not None


def test_parse_search_results_skips_malformed_items() -> None:
    payload = {
        "items": [
            {"full_name": "ok/repo", "html_url": "https://github.com/ok/repo",
             "pushed_at": "2026-10-01T00:00:00Z",
             "license": {"spdx_id": "MIT"}},
            {"full_name": "broken/repo"},  # missing required fields
            "not-a-dict",
        ]
    }
    repos = parse_search_results(payload)
    assert [repo.full_name for repo in repos] == ["ok/repo"]


def test_hard_filter_drops_archived_and_non_osi(invoice_search_payload) -> None:
    repos = parse_search_results(invoice_search_payload)
    survivors = hard_filter(repos)
    names = {repo.full_name for repo in survivors}
    assert len(survivors) == 6
    assert names.isdisjoint(DECOY_FULL_NAMES)


def test_service_returns_ranked_candidates_without_decoys(invoice_search_payload) -> None:
    github = FakeGitHubSearch(invoice_search_payload)
    candidates = DiscoveryService(github).search("a free invoice maker")
    assert 3 <= len(candidates) <= 5
    names = [candidate.full_name for candidate in candidates]
    assert set(names).isdisjoint(DECOY_FULL_NAMES)
    stars = [candidate.stars for candidate in candidates]
    assert stars == sorted(stars, reverse=True)
    assert [candidate.id for candidate in candidates] == list(
        range(1, len(candidates) + 1)
    )


def test_service_passes_query_through_literally(invoice_search_payload) -> None:
    github = FakeGitHubSearch(invoice_search_payload)
    DiscoveryService(github).search("offline video trimmer")
    assert github.queries == ["offline video trimmer"]


# --- plain-English formatting (spec user story 3) ----------------------------


def test_format_stars_uses_thousands_separator() -> None:
    assert format_stars(12400) == "12,400 stars"
    assert format_stars(950) == "950 stars"


def test_format_license_explains_known_licenses_in_plain_english() -> None:
    assert format_license("MIT").startswith("MIT — permissive")
    assert "patent" in format_license("Apache-2.0")
    assert "copyleft" in format_license("GPL-3.0-only")
    assert "OSI-approved" in format_license("Zlib")  # fallback still honest


def test_format_updated_relative_phrases() -> None:
    def days_ago(n: int) -> datetime:
        return NOW - timedelta(days=n)

    assert format_updated(NOW - timedelta(hours=2), NOW) == "today"
    assert format_updated(days_ago(1), NOW) == "yesterday"
    assert format_updated(days_ago(14), NOW) == "14 days ago"
    assert format_updated(days_ago(60), NOW) == "2 months ago"
    assert format_updated(days_ago(400), NOW) == "1 year ago"
    assert format_updated(NOW - timedelta(days=2), NOW) == "2 days ago"


def test_maintenance_signal_tiers() -> None:
    active = maintenance_signal(NOW - timedelta(days=20), NOW)
    occasional = maintenance_signal(NOW - timedelta(days=200), NOW)
    dormant = maintenance_signal(NOW - timedelta(days=800), NOW)
    assert active.startswith("Active")
    assert occasional.startswith("Occasional commits")
    assert dormant.startswith("Dormant")
    for signal in (active, occasional, dormant):
        assert "last commit" in signal


# --- live client, hermetically via httpx.MockTransport ----------------------


def _client_with(handler) -> GitHubSearchClient:
    return GitHubSearchClient("github_pat_test", transport=httpx.MockTransport(handler))


def test_client_sends_auth_and_parses_response(invoice_search_payload) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization")
        seen["q"] = request.url.params.get("q")
        return httpx.Response(200, json=invoice_search_payload)

    repos = _client_with(handler).search("free invoice maker")
    assert seen["authorization"] == "Bearer github_pat_test"
    assert seen["q"] == "free invoice maker"
    assert len(repos) == 10


def test_client_401_explains_the_token_problem() -> None:
    client = _client_with(lambda request: httpx.Response(401, json={}))
    with pytest.raises(GitHubAPIError, match="FORAGE_GITHUB_TOKEN"):
        client.search("anything")


def test_client_rate_limit_message() -> None:
    client = _client_with(lambda request: httpx.Response(403, json={}))
    with pytest.raises(GitHubAPIError, match="rate limit"):
        client.search("anything")


def test_client_network_failure_is_friendly() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(GitHubAPIError, match="Couldn't reach GitHub"):
        _client_with(handler).search("anything")
