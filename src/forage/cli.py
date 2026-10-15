"""Forage CLI — composition root (ADR-0002: Windows CLI first for v1)."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console

from forage import __version__
from forage.config import ConfigError, load_settings
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
    _print_not_implemented("find", "issues #3 and #4")
    raise typer.Exit(code=1)


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
