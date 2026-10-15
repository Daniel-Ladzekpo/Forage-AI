"""Forage CLI — composition root (ADR-0002: Windows CLI first for v1)."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from forage import __version__
from forage.config import ConfigError, load_settings
from forage.discovery import (
    MIN_COMFORTABLE_CANDIDATES,
    Candidate,
    DiscoveryService,
    GitHubAPIError,
    GitHubSearchClient,
    format_license,
    format_stars,
    maintenance_signal,
    utcnow,
)
from forage.setup_wizard import print_setup

app = typer.Typer(
    help=(
        "Forage AI — describe what you need, get 3-5 trustworthy open-source "
        "picks, and turn one into something double-clickable on Windows."
    ),
    no_args_is_help=True,
    add_completion=False,
)

# stdout so setup guidance shows up in pipes, CI logs, and test runners alike.
console = Console()


def _print_config_error(missing: list[str]) -> None:
    count = len(missing)
    console.print(
        f"[red]Forage can't run yet — {count} required environment "
        f"{'variable is' if count == 1 else 'variables are'} not set:[/red]\n"
    )
    for name in missing:
        console.print(f"  [red]✗[/red] {name}")
    console.print(
        "\nForage reads configuration from environment variables only "
        "(no config files).\nRun [bold]forage setup[/bold] for step-by-step "
        "instructions."
    )


def _print_not_implemented(command: str, issues: str) -> None:
    console.print(
        f"[yellow]`forage {command}` is not implemented yet — "
        f"tracked in {issues}.[/yellow]"
    )


def _render_candidates(discovery_query: str, candidates: list[Candidate]) -> None:
    """Render Candidate cards: stars, license, maintenance in plain English."""
    now = utcnow()
    console.print(f'[bold]Candidates for[/bold] "{discovery_query}"')
    for candidate in candidates:
        lines: list[str] = []
        if candidate.description:
            lines.append(candidate.description)
        lines.append(f"Stars: {format_stars(candidate.stars)}")
        lines.append(f"License: {format_license(candidate.license_spdx)}")
        lines.append(
            f"Maintenance: {maintenance_signal(candidate.pushed_at, now)}"
        )
        if candidate.why_pick:
            lines.append(f"Best for: {candidate.why_pick}")
        if candidate.why_not:
            lines.append(f"Tradeoff: {candidate.why_not}")
        lines.append(candidate.html_url)
        console.print(
            Panel(
                "\n".join(lines),
                title=f"{candidate.id}. {candidate.full_name}",
                title_align="left",
            )
        )


def requires_config(func: Callable[..., Any]) -> Callable[..., Any]:
    """Fail fast with setup guidance when any required env var is missing."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            load_settings()
        except ConfigError as exc:
            _print_config_error(exc.missing)
            raise typer.Exit(code=1) from exc
        return func(*args, **kwargs)

    return wrapper


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"forage {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the Forage version and exit.",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    """Forage AI — describe → suggest → package/shortcut."""


@app.command("setup")
def setup() -> None:
    """Print first-run setup instructions (GitHub token + Anthropic key)."""
    print_setup(console)


@app.command("find")
@requires_config
def find(
    discovery_query: str = typer.Argument(
        ...,
        help='Plain-English description, e.g. "a simple offline video trimmer".',
    ),
) -> None:
    """Describe what you need; Forage suggests 3-5 trustworthy Candidates."""
    settings = load_settings()
    service = DiscoveryService(GitHubSearchClient(token=settings.github_token))
    try:
        candidates = service.search(discovery_query)
    except GitHubAPIError as exc:
        console.print(f"[red]Search failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    if not candidates:
        console.print(
            f'[yellow]No trustworthy Candidates found[/yellow] for '
            f'"{discovery_query}".\nArchived and non-OSI-licensed repos are '
            "dropped by hard filter — try a broader description."
        )
        return
    _render_candidates(discovery_query, candidates)
    if len(candidates) < MIN_COMFORTABLE_CANDIDATES:
        noun = "match" if len(candidates) == 1 else "matches"
        console.print(
            f"\n[yellow]Only {len(candidates)} trustworthy {noun} found[/yellow]"
            " — try a broader description for more options."
        )


@app.command("install")
@requires_config
def install(
    candidate_id: str = typer.Argument(
        ...,
        help="Candidate id from `forage find`, e.g. 2.",
    ),
) -> None:
    """Package or shortcut a Candidate (Risk Card + consent first)."""
    _print_not_implemented("install", "issues #5-#8")
    raise typer.Exit(code=1)
