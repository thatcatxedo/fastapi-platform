"""fp push — push local code as draft (no deploy)."""

import typer

from ..api.client import PlatformClient, PlatformError, resolve_app
from ..config import get_active_platform_or_exit
from ..console import console, err_console
from ..project import read_project, collect_files, detect_mode


def push():
    """Push local code to the platform as a draft (no deploy)."""
    project = read_project()
    app_name = project.get("name")
    entrypoint = project.get("entrypoint", "app.py")

    if not app_name:
        err_console.print("[red]No 'name' field in .fp.yaml[/red]")
        raise typer.Exit(1)

    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    app = resolve_app(client, app_name)

    files = collect_files(entrypoint=entrypoint)
    mode = detect_mode(files)

    payload: dict = {}
    if mode == "multi":
        payload["files"] = files
    else:
        payload["code"] = files[entrypoint]

    try:
        client.save_draft(app["app_id"], payload)
    except PlatformError as e:
        err_console.print(f"[red]Push failed:[/red] {e.message}")
        raise typer.Exit(1)

    console.print(f"Pushed draft for [bold]{app_name}[/bold] ({len(files)} file{'s' if len(files) != 1 else ''})")
    console.print("  Run [bold]fp deploy[/bold] to publish these changes.")
