"""ArguPaper CLI - Command-line interface for paper analysis."""

import typer

from argupaper.cli.commands import analyze, search

app = typer.Typer(
    name="argupaper",
    help="ArguPaper - Multi-Agent Research Cognition System",
    add_completion=False,
)

# Register commands
app.command("analyze")(analyze)
app.command("search")(search)


@app.callback(invoke_without_command=True)
def cli_main(ctx: typer.Context) -> None:
    """ArguPaper - Multi-Agent Research Cognition System.

    A research cognition system providing paper retrieval → understanding
    → evidence analysis → adversarial critique → consensus generation.

    Examples:

        argupaper analyze ./paper.pdf --output report.md

        argupaper search "machine learning theory" --limit 10
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    app()
