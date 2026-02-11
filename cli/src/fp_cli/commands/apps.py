"""fp list, fp status, fp open, fp delete — app management commands."""

import webbrowser
from urllib.parse import urlparse

import typer
from rich.table import Table

from ..api.client import PlatformClient, PlatformError, resolve_app
from ..config import get_active_platform_or_exit
from ..console import console, err_console
from ..project import read_project, find_project_file


def _get_app_domain(platform_url: str) -> str:
    """Derive app domain from platform URL."""
    host = urlparse(platform_url).hostname or ""
    if host.startswith("platform."):
        return host[len("platform."):]
    return host


def _get_app_url(app_id: str, platform_url: str) -> str:
    return f"https://app-{app_id}.{_get_app_domain(platform_url)}"


def _resolve_app_name(name: str | None) -> str:
    """Resolve app name from argument or .fp.yaml."""
    if name:
        return name
    fp_file = find_project_file()
    if fp_file:
        import yaml

        data = yaml.safe_load(fp_file.read_text()) or {}
        if data.get("name"):
            return data["name"]
    err_console.print("[red]No app name provided and no .fp.yaml found.[/red]")
    raise typer.Exit(1)


def list_apps():
    """List all your apps."""
    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    try:
        apps = client.list_apps()
    except PlatformError as e:
        err_console.print(f"[red]Failed to list apps:[/red] {e.message}")
        raise typer.Exit(1)

    if not apps:
        console.print("[dim]No apps yet.[/dim] Run [bold]fp init[/bold] + [bold]fp deploy[/bold] to create one.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("URL")
    table.add_column("Last Deploy")

    for app in apps:
        status = app.get("status", "unknown")
        style = {
            "running": "green",
            "deploying": "yellow",
            "error": "red",
            "failed": "red",
        }.get(status, "dim")

        url = _get_app_url(app["app_id"], platform["url"])
        last_deploy = app.get("last_deploy_at") or app.get("created_at") or ""
        if last_deploy and "T" in last_deploy:
            last_deploy = last_deploy.split("T")[0]

        table.add_row(
            app["name"],
            f"[{style}]{status}[/{style}]",
            url,
            last_deploy,
        )

    console.print(table)


def status(name: str = typer.Argument(None, help="App name (uses .fp.yaml if omitted)")):
    """Show app status."""
    app_name = _resolve_app_name(name)
    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    app = resolve_app(client, app_name)
    app_url = _get_app_url(app["app_id"], platform["url"])

    try:
        ds = client.deploy_status(app["app_id"])
    except PlatformError:
        ds = {}

    app_status = ds.get("status") or app.get("status", "unknown")
    ready = ds.get("deployment_ready", False)

    style = "green" if app_status == "running" and ready else "yellow" if app_status == "deploying" else "red" if app_status in ("error", "failed") else "dim"

    console.print(f"  Name:   [bold]{app['name']}[/bold]")
    console.print(f"  Status: [{style}]{app_status}[/{style}]")
    console.print(f"  Ready:  {'yes' if ready else 'no'}")
    console.print(f"  URL:    {app_url}")
    console.print(f"  ID:     {app['app_id']}")
    if ds.get("last_error"):
        console.print(f"  Error:  [red]{ds['last_error']}[/red]")


def open_app(name: str = typer.Argument(None, help="App name (uses .fp.yaml if omitted)")):
    """Open app URL in browser."""
    app_name = _resolve_app_name(name)
    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    app = resolve_app(client, app_name)
    url = _get_app_url(app["app_id"], platform["url"])

    console.print(f"Opening [link={url}]{url}[/link]")
    webbrowser.open(url)


def delete(
    name: str = typer.Argument(..., help="App name to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete an app."""
    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    app = resolve_app(client, name)

    if not yes:
        confirm = typer.confirm(f"Delete app '{app['name']}'? This cannot be undone")
        if not confirm:
            raise typer.Abort()

    try:
        client.delete_app(app["app_id"])
    except PlatformError as e:
        err_console.print(f"[red]Delete failed:[/red] {e.message}")
        raise typer.Exit(1)

    console.print(f"Deleted [bold]{app['name']}[/bold]")
