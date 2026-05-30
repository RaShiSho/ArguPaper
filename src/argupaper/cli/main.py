"""ArguPaper CLI entrypoint."""

import typer

from argupaper import __version__
from argupaper.cli.commands import analyze, convert, papers, search

app = typer.Typer(
    name="argupaper",
    help="ArguPaper - Multi-Agent Research Cognition System",
    add_completion=False,
)

app.command("analyze")(analyze)
app.command("convert")(convert)
app.command("papers")(papers)
app.command("search")(search)


@app.callback(invoke_without_command=True)
def cli_main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the installed version and exit.",
        is_eager=True,
    ),
) -> None:
    """ArguPaper - Multi-Agent Research Cognition System."""

    if version:
        typer.echo(__version__)
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def main() -> None:
    """Entry point for the CLI."""

    app()


if __name__ == "__main__":
    app()
