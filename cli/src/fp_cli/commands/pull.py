"""fp pull — pull app code to local directory."""

from pathlib import Path

import typer

from ..api.client import PlatformClient, PlatformError, resolve_app
from ..config import get_active_platform_or_exit
from ..console import console, err_console
from ..project import write_project, PROJECT_FILE


def pull(
    name: str = typer.Argument(..., help="App name to pull"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
):
    """Pull app code from the platform to the current directory."""
    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    app = resolve_app(client, name)

    try:
        detail = client.get_app(app["app_id"])
    except PlatformError as e:
        err_console.print(f"[red]Failed to get app details:[/red] {e.message}")
        raise typer.Exit(1)

    cwd = Path.cwd()

    # Check for existing .fp.yaml
    if (cwd / PROJECT_FILE).exists() and not force:
        err_console.print(
            f"[yellow]{PROJECT_FILE} already exists.[/yellow] Use [bold]--force[/bold] to overwrite."
        )
        raise typer.Exit(1)

    mode = detail.get("mode", "single")
    written = 0

    if mode == "multi" and detail.get("files"):
        files = detail["files"]
        # Prefer deployed files, fall back to draft
        if detail.get("deployed_files"):
            files = detail["deployed_files"]
        for filename, content in files.items():
            filepath = cwd / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
            written += 1
    elif detail.get("code") or detail.get("deployed_code"):
        code = detail.get("deployed_code") or detail.get("code", "")
        (cwd / "app.py").write_text(code)
        written = 1
    else:
        err_console.print("[red]App has no code to pull.[/red]")
        raise typer.Exit(1)

    # Write project file
    entrypoint = detail.get("entrypoint") or "app.py"
    project_data = {"name": detail["name"], "entrypoint": entrypoint}
    write_project(project_data)

    console.print(f"Pulled [bold]{detail['name']}[/bold] ({written} file{'s' if written != 1 else ''})")
    console.print(f"  Written to: {cwd}")
