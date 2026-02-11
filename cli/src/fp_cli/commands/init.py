"""fp init — scaffold a new project."""

from pathlib import Path

import typer
from rich.prompt import Prompt

from ..api.client import PlatformClient, PlatformError
from ..config import get_active_platform
from ..console import console, err_console
from ..project import write_project, PROJECT_FILE

FASTAPI_STARTER = '''\
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Hello from FastAPI Platform!"}
'''

FASTHTML_STARTER = '''\
from fasthtml.common import *

app, rt = fast_app()


@rt("/")
def home():
    return H1("Hello from FastAPI Platform!")
'''


def init(
    template: str = typer.Option("", "--template", "-t", help="Create from a platform template"),
    name: str = typer.Option("", "--name", "-n", help="App name (default: directory name)"),
):
    """Scaffold a new project in the current directory."""
    cwd = Path.cwd()

    # Check if .fp.yaml already exists
    if (cwd / PROJECT_FILE).exists():
        err_console.print(f"[yellow]{PROJECT_FILE} already exists in this directory.[/yellow]")
        raise typer.Exit(1)

    app_name = name or cwd.name

    if template:
        _init_from_template(template, app_name)
        return

    # Interactive: pick framework
    framework = Prompt.ask(
        "Framework",
        choices=["fastapi", "fasthtml"],
        default="fastapi",
    )

    code = FASTAPI_STARTER if framework == "fastapi" else FASTHTML_STARTER

    # Write files
    (cwd / "app.py").write_text(code)
    write_project({"name": app_name, "entrypoint": "app.py"})

    console.print(f"Created [bold]app.py[/bold] + [bold]{PROJECT_FILE}[/bold]")
    console.print(f"  App name: [cyan]{app_name}[/cyan]")
    console.print(f"  Framework: {framework}")
    console.print()
    console.print("Next steps:")
    console.print("  [bold]fp dev[/bold]     — run locally with hot reload")
    console.print("  [bold]fp deploy[/bold]  — deploy to the platform")


def _init_from_template(template_name: str, app_name: str):
    """Initialize from a platform template."""
    platform = get_active_platform()
    if not platform:
        err_console.print(
            "[red]Not authenticated.[/red] "
            "Run [bold]fp auth login <url>[/bold] to use templates from the platform."
        )
        raise typer.Exit(1)

    client = PlatformClient(platform["url"], platform["token"])

    try:
        templates = client.list_templates()
    except PlatformError as e:
        err_console.print(f"[red]Failed to fetch templates:[/red] {e.message}")
        raise typer.Exit(1)

    # Find template by name (case-insensitive)
    match = None
    for t in templates:
        if t["name"].lower() == template_name.lower():
            match = t
            break

    if not match:
        err_console.print(f"[red]Template '{template_name}' not found.[/red]")
        err_console.print("Available templates:")
        for t in templates:
            console.print(f"  - {t['name']}")
        raise typer.Exit(1)

    cwd = Path.cwd()

    # Write template files
    if match.get("mode") == "multi" and match.get("files"):
        for filename, content in match["files"].items():
            filepath = cwd / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
        console.print(f"Created {len(match['files'])} files from template [bold]{match['name']}[/bold]")
    elif match.get("code"):
        (cwd / "app.py").write_text(match["code"])
        console.print(f"Created [bold]app.py[/bold] from template [bold]{match['name']}[/bold]")
    else:
        err_console.print("[red]Template has no code or files.[/red]")
        raise typer.Exit(1)

    # Write project file
    entrypoint = match.get("entrypoint", "app.py")
    write_project({"name": app_name, "entrypoint": entrypoint})

    console.print(f"  App name: [cyan]{app_name}[/cyan]")
    console.print()
    console.print("Next steps:")
    console.print("  [bold]fp dev[/bold]     — run locally with hot reload")
    console.print("  [bold]fp deploy[/bold]  — deploy to the platform")
