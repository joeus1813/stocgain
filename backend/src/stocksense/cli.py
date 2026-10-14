"""Command namespace reserved for the phased implementation."""

import typer

app = typer.Typer(no_args_is_help=True, help="StockSense batch and database commands.")


def not_implemented() -> None:
    """Fail explicitly until a later phase implements this command group."""
    typer.echo(
        "Not implemented: this command requires a later implementation phase.", err=True
    )
    raise typer.Exit(2)


for name in ("data", "db", "analytics", "pipeline"):
    group = typer.Typer(invoke_without_command=True, callback=not_implemented)
    app.add_typer(group, name=name)
