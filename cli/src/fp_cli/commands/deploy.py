"""fp deploy — deploy to the platform."""

import time

import typer
from rich.live import Live
from rich.spinner import Spinner

from ..api.client import PlatformClient, PlatformError, resolve_app
from ..config import get_active_platform_or_exit
from ..console import console, err_console
from ..project import read_project, collect_files, detect_mode

PHASE_LABELS = {
    "validating": "Validating code...",
    "creating_resources": "Creating Kubernetes resources...",
    "pending": "Waiting to be scheduled...",
    "scheduled": "Pod scheduled...",
    "pulling": "Pulling container image...",
    "pulled": "Image pulled...",
    "creating": "Creating container...",
    "starting": "Starting application...",
    "ready": "Application ready!",
    "error": "Deployment error",
}


def deploy():
    """Deploy the current project to the platform."""
    project = read_project()
    app_name = project.get("name")
    entrypoint = project.get("entrypoint", "app.py")

    if not app_name:
        err_console.print("[red]No 'name' field in .fp.yaml[/red]")
        raise typer.Exit(1)

    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    # Collect files from directory
    files = collect_files(entrypoint=entrypoint)
    mode = detect_mode(files)

    console.print(f"Deploying [bold]{app_name}[/bold] to {platform['url']}")
    if mode == "multi":
        console.print(f"  {len(files)} files, mode: multi-file")
    else:
        console.print(f"  mode: single-file")

    # Check if app already exists (update vs create)
    existing_apps = client.list_apps()
    existing = next((a for a in existing_apps if a["name"] == app_name), None)

    # Build payload
    payload: dict = {"name": app_name}
    if mode == "multi":
        payload["files"] = files
        payload["mode"] = "multi"
        payload["entrypoint"] = entrypoint
    else:
        payload["code"] = files[entrypoint]
        payload["mode"] = "single"

    # Include env vars from .fp.yaml if present
    env = project.get("env")
    if env and isinstance(env, dict):
        import os

        resolved = {}
        for key, value in env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                resolved[key] = os.environ.get(env_name, "")
            else:
                resolved[key] = str(value)
        payload["env_vars"] = resolved

    try:
        if existing:
            result = client.update_app(existing["app_id"], payload)
            console.print(f"  Updating existing app ({existing['app_id']})")
        else:
            result = client.create_app(payload)
            console.print(f"  Created new app ({result.get('app_id', 'unknown')})")
    except PlatformError as e:
        err_console.print(f"\n[red]Deploy failed:[/red] {e.message}")
        raise typer.Exit(1)

    app_id = result.get("app_id") or (existing and existing["app_id"])
    if not app_id:
        err_console.print("[red]No app_id in response[/red]")
        raise typer.Exit(1)

    # Poll deployment status
    _poll_deploy_status(client, app_id, platform["url"])


def _poll_deploy_status(client: PlatformClient, app_id: str, platform_url: str):
    """Poll deploy-status until ready, error, or timeout."""
    max_polls = 60
    poll_interval = 2

    with Live(
        Spinner("dots", text="Creating resources..."),
        console=console,
        transient=True,
    ) as live:
        for i in range(max_polls):
            try:
                status = client.deploy_status(app_id)
            except PlatformError:
                time.sleep(poll_interval)
                continue

            phase = "creating_resources"
            if status.get("deployment_ready"):
                phase = "ready"
            elif status.get("status") == "error":
                phase = "error"
            elif status.get("deploy_stage"):
                phase = status["deploy_stage"]

            label = PHASE_LABELS.get(phase, phase)
            live.update(Spinner("dots", text=label))

            if phase == "ready":
                break
            if phase == "error":
                err_console.print(
                    f"\n[red]Deployment failed:[/red] {status.get('last_error', 'Unknown error')}"
                )
                raise typer.Exit(1)

            time.sleep(poll_interval)
        else:
            err_console.print(
                "\n[yellow]Deployment is still in progress.[/yellow] "
                "Check status with [bold]fp status[/bold]"
            )
            raise typer.Exit(1)

    # Derive app URL from platform URL
    # platform.gatorlunch.com -> app-{id}.gatorlunch.com
    from urllib.parse import urlparse

    parsed = urlparse(platform_url)
    host = parsed.hostname or ""
    # Strip "platform." prefix to get the app domain
    if host.startswith("platform."):
        app_domain = host[len("platform."):]
    else:
        app_domain = host
    app_url = f"https://app-{app_id}.{app_domain}"

    console.print()
    console.print("[green]Deployed successfully![/green]")
    console.print(f"  URL: [bold link={app_url}]{app_url}[/bold link]")
    console.print(f"  Docs: [link={app_url}/docs]{app_url}/docs[/link]")
