"""Discovery: GitHub search, hard filters, and Candidate building.

Seam 1 of the approved test seams: ``DiscoveryService.search(discoveryQuery)``
takes an injected GitHub search client, so tests run against recorded API
fixtures with no live network. No LLM is involved yet — query expansion and
re-ranking arrive with issue #4; for now the literal query text is searched
and Candidates are ranked by stars.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import httpx
from pydantic import BaseModel, ValidationError

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_API_VERSION = "2022-11-28"
SEARCH_PAGE_SIZE = 30
MAX_CANDIDATES = 5
MIN_COMFORTABLE_CANDIDATES = 3

# Hard filter (spec user story 11): allowlist of OSI-approved SPDX ids that
# GitHub's search API actually returns. Anything else — non-OSI licenses
# (e.g. BUSL-1.1), NOASSERTION, or no license at all — is blocked by default.
OSI_APPROVED_SPDX_IDS = frozenset(
    {
        "0BSD", "AFL-3.0", "Apache-1.1", "Apache-2.0", "Artistic-2.0",
        "BSL-1.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CDDL-1.0",
        "CDDL-1.1", "CPAL-1.0", "EPL-2.0", "EUPL-1.2", "GPL-2.0",
        "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0", "GPL-3.0-only",
        "GPL-3.0-or-later", "IPL-1.0", "ISC", "LGPL-2.0", "LGPL-2.1",
        "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0", "LGPL-3.0-only",
        "LGPL-3.0-or-later", "MIT", "MIT-0", "MPL-2.0", "MS-PL", "MS-RL",
        "NCSA", "OSL-3.0", "PostgreSQL", "Unlicense", "WTFPL", "X11",
        "Zlib", "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
        "Ruby", "Beerware", "HPND", "Old-MIT", "Sendmail",
    }
)

LICENSE_PLAIN_ENGLISH: dict[str, str] = {
    "MIT": "MIT — permissive; free to use, modify, and redistribute",
    "Apache-2.0": "Apache-2.0 — permissive with patent protection",
    "BSD-2-Clause": "BSD-2-Clause — permissive",
    "BSD-3-Clause": "BSD-3-Clause — permissive; no endorsement rights",
    "0BSD": "0BSD — public domain, no conditions",
    "ISC": "ISC — permissive (MIT-like)",
    "GPL-2.0": "GPL-2.0 — copyleft; derivatives must stay open",
    "GPL-2.0-only": "GPL-2.0-only — copyleft; derivatives must stay open",
    "GPL-2.0-or-later": "GPL-2.0-or-later — copyleft; derivatives must stay open",
    "GPL-3.0": "GPL-3.0 — copyleft; derivatives must stay open",
    "GPL-3.0-only": "GPL-3.0-only — copyleft; derivatives must stay open",
    "GPL-3.0-or-later": "GPL-3.0-or-later — copyleft; derivatives must stay open",
    "LGPL-2.1": "LGPL-2.1 — copyleft for libraries; apps may link",
    "LGPL-3.0": "LGPL-3.0 — copyleft for libraries; apps may link",
    "AGPL-3.0": "AGPL-3.0 — strong copyleft, applies over the network",
    "AGPL-3.0-only": "AGPL-3.0-only — strong copyleft, applies over the network",
    "MPL-2.0": "MPL-2.0 — file-level copyleft; your changes to its files stay open",
    "Unlicense": "Unlicense — public domain dedication",
    "CC0-1.0": "CC0-1.0 — public domain dedication",
}


class GitHubAPIError(Exception):
    """A GitHub search failure with a user-facing explanation."""


class Repository(BaseModel):
    """The subset of a GitHub search result Forage needs for Discovery."""

    full_name: str
    html_url: str
    description: str | None = None
    stars: int = 0
    pushed_at: datetime
    archived: bool = False
    license_spdx: str | None = None
    topics: list[str] = []


class Candidate(BaseModel):
    """A repository that passed hard filters, presented to the user.

    ``why_pick``/``why_not`` are filled in by the LLM layer (issue #4);
    ``packageability`` and ``risk_signals`` arrive with the Packager (#7)
    and Risk Gate (#5).
    """

    id: int
    full_name: str
    html_url: str
    description: str | None = None
    stars: int
    pushed_at: datetime
    license_spdx: str
    topics: list[str] = []
    why_pick: str | None = None
    why_not: str | None = None

    @classmethod
    def from_repository(cls, candidate_id: int, repo: Repository) -> "Candidate":
        # Unlicensed repos never reach this point (hard filter), so a
        # license_spdx of None here would be a bug upstream.
        assert repo.license_spdx is not None, "unlicensed repo passed hard filter"
        return cls(
            id=candidate_id,
            full_name=repo.full_name,
            html_url=repo.html_url,
            description=repo.description,
            stars=repo.stars,
            pushed_at=repo.pushed_at,
            license_spdx=repo.license_spdx,
            topics=repo.topics,
        )


def parse_search_results(payload: dict) -> list[Repository]:
    """Parse a GitHub ``/search/repositories`` response into Repositories.

    Shared by the live client and the recorded-fixture fake so both paths
    exercise identical parsing. Malformed items are skipped, never fatal.
    """
    repositories: list[Repository] = []
    for item in payload.get("items", []):
        try:
            license_info = item.get("license") or {}
            repositories.append(
                Repository(
                    full_name=item["full_name"],
                    html_url=item["html_url"],
                    description=item.get("description"),
                    stars=item.get("stargazers_count", 0),
                    pushed_at=item["pushed_at"],
                    archived=item.get("archived", False),
                    license_spdx=license_info.get("spdx_id"),
                    topics=item.get("topics") or [],
                )
            )
        except (AttributeError, ValidationError, KeyError, TypeError):
            continue
    return repositories


def passes_hard_filters(repo: Repository) -> bool:
    """Archived and non-OSI/unknown-licensed repos never become Candidates."""
    return not repo.archived and repo.license_spdx in OSI_APPROVED_SPDX_IDS


def hard_filter(repositories: list[Repository]) -> list[Repository]:
    return [repo for repo in repositories if passes_hard_filters(repo)]


def format_stars(stars: int) -> str:
    return f"{stars:,} stars"


def format_license(spdx: str) -> str:
    return LICENSE_PLAIN_ENGLISH.get(spdx, f"{spdx} — OSI-approved license")


def _days_since(pushed_at: datetime, now: datetime) -> int:
    return max((now - pushed_at).days, 0)


def format_updated(pushed_at: datetime, now: datetime) -> str:
    """Relative time in plain English: 'yesterday', '14 days ago', ..."""
    seconds = max((now - pushed_at).total_seconds(), 0.0)
    days = seconds / 86_400
    if seconds < 3_600:
        return "just now"
    if days < 1:
        return "today"
    if days < 2:
        return "yesterday"
    if days < 30:
        return f"{int(days)} days ago"
    if days < 365:
        months = max(int(days // 30), 1)
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = int(days // 365)
    return f"{years} year{'s' if years != 1 else ''} ago"


def maintenance_signal(pushed_at: datetime, now: datetime) -> str:
    """Maintenance signal in plain English (spec user story 3)."""
    days = _days_since(pushed_at, now)
    relative = format_updated(pushed_at, now)
    if days <= 90:
        return f"Active — last commit {relative}"
    if days <= 365:
        return f"Occasional commits — last commit {relative}"
    return f"Dormant — last commit {relative}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GitHubSearch(Protocol):
    """The seam DiscoveryService depends on (fake it in tests)."""

    def search(self, query: str) -> list[Repository]: ...


class GitHubSearchClient:
    """Live GitHub repository search, authenticated with the user's PAT."""

    def __init__(
        self,
        token: str,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
                "User-Agent": "forage-ai",
            },
        )

    def search(self, query: str) -> list[Repository]:
        try:
            response = self._http.get(
                GITHUB_SEARCH_URL,
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": SEARCH_PAGE_SIZE,
                },
            )
        except httpx.RequestError as exc:
            raise GitHubAPIError(
                "Couldn't reach GitHub — check your internet connection and try again."
            ) from exc
        if response.status_code == 401:
            raise GitHubAPIError(
                "GitHub rejected your token (401). Re-check FORAGE_GITHUB_TOKEN — "
                "run `forage setup` for how to create a fresh one."
            )
        if response.status_code in (403, 429):
            raise GitHubAPIError(
                "GitHub said 'slow down' (rate limit reached). Wait a minute and "
                "try the same query again."
            )
        if response.status_code != 200:
            raise GitHubAPIError(
                f"GitHub search failed with HTTP {response.status_code}. Try again shortly."
            )
        return parse_search_results(response.json())


class DiscoveryService:
    """Literal GitHub search → hard filters → up to 3-5 ranked Candidates."""

    def __init__(self, github: GitHubSearch) -> None:
        self._github = github

    def search(
        self, discovery_query: str, *, limit: int = MAX_CANDIDATES
    ) -> list[Candidate]:
        repositories = self._github.search(discovery_query)
        filtered = hard_filter(repositories)
        filtered.sort(key=lambda repo: repo.stars, reverse=True)
        return [
            Candidate.from_repository(candidate_id, repo)
            for candidate_id, repo in enumerate(filtered[:limit], start=1)
        ]

