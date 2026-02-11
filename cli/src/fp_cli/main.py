"""fp — CLI for the FastAPI Platform"""

import typer

from . import __version__
from .commands import auth
from .commands.init import init
from .commands.deploy import deploy
from .commands.apps import list_apps, status, open_app, delete
from .commands.logs import logs
from .commands.validate import validate
from .commands.dev import dev
from .commands.pull import pull
from .commands.push import push

app = typer.Typer(
    name="fp",
    help="Deploy Python APIs from your terminal.",
    no_args_is_help=True,
    add_completion=False,
)

# Auth is a subcommand group: fp auth login, fp auth whoami, fp auth logout
app.add_typer(auth.app, name="auth")

# Top-level commands
app.command()(init)
app.command()(deploy)
app.command(name="list")(list_apps)
app.command()(status)
app.command(name="open")(open_app)
app.command()(delete)
app.command()(logs)
app.command()(validate)
app.command()(dev)
app.command()(pull)
app.command()(push)


@app.command()
def version():
    """Show fp-cli version."""
    typer.echo(f"fp-cli {__version__}")


if __name__ == "__main__":
    app()
