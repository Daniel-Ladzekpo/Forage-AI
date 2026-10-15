"""First-run setup wizard: step-by-step instructions for the required env vars.

Per round-2 decision Q4 the CLI never prompts for secrets interactively and
never writes them anywhere; ``forage setup`` only *prints* how to create them.
"""

from __future__ import annotations

from rich.console import Console

from forage.config import GITHUB_TOKEN_ENV, LLM_API_KEY_ENV

GITHUB_PAT_URL = "https://github.com/settings/personal-access-tokens/new"
ANTHROPIC_CONSOLE_URL = "https://console.anthropic.com/"


def _numbered(console: Console, steps: list[str]) -> None:
    """Print numbered steps; entries starting with two spaces are continuations."""
    number = 0
    for step in steps:
        if step.startswith("  "):
            console.print(f"     {step.strip()}")
        else:
            number += 1
            console.print(f"  {number}. {step}")


def print_setup(console: Console) -> None:
    """Print the first-run setup instructions."""
    console.print("[bold]Forage first-run setup[/bold]\n")
    console.print(
        "Forage reads two secrets from environment variables only. It never\n"
        "stores them in config files, never hardcodes them, and never asks\n"
        "for them interactively.\n"
    )
    console.print(
        f"  [cyan]{GITHUB_TOKEN_ENV:<21}[/cyan]read-only GitHub access for Discovery"
    )
    console.print(
        f"  [cyan]{LLM_API_KEY_ENV:<21}[/cyan]expand/rank queries (Anthropic)\n"
    )

    console.print("[bold]Step 1 — Create a fine-grained, read-only GitHub token[/bold]")
    _numbered(
        console,
        [
            f"Open {GITHUB_PAT_URL}",
            "  (GitHub -> Settings -> Developer settings -> Personal access",
            "   tokens -> Fine-grained tokens -> Generate new token)",
            'Name it "forage"; Resource owner: your account.',
            'Repository access -> select "Public repositories (read-only)".',
            "Leave Account permissions empty — read-only is enough.",
            "Set an expiration you are comfortable with (e.g. 90 days).",
            'Click "Generate token" and copy it right away (github_pat_...).',
            f"Persist it:  setx {GITHUB_TOKEN_ENV} \"github_pat_...\"",
            "  then open a NEW terminal — setx does not update open windows.",
            'Alternative: Win key -> "environment variables" -> "Edit the',
            '   environment variables for your account" -> New -> paste it.',
        ],
    )
    console.print()

    console.print("[bold]Step 2 — Get an Anthropic API key[/bold]")
    _numbered(
        console,
        [
            f"Open {ANTHROPIC_CONSOLE_URL} and sign in (or create an account).",
            'Go to API Keys -> Create Key, name it "forage", copy it',
            "  (it starts with sk-ant-...).",
            "API usage is pay-as-you-go; consider setting a spend limit.",
            f"Persist it:  setx {LLM_API_KEY_ENV} \"sk-ant-...\"",
            "  then open a NEW terminal.",
        ],
    )
    console.print()

    console.print("[bold]Step 3 — Verify[/bold]")
    _numbered(
        console,
        [
            'Open a new terminal and run:  forage find "a simple offline video trimmer"',
            "If setup is complete you get 3-5 Candidate cards instead of an error.",
        ],
    )
    console.print(
        "\n[yellow]Keep both keys secret.[/yellow] Forage never writes them to disk;"
        " leaking either key means revoking it where it was created."
    )
