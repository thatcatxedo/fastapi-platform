"""fp logs — tail app logs."""

import json
import re

import typer

from ..api.client import PlatformClient, PlatformError, resolve_app
from ..config import get_active_platform_or_exit
from ..console import console, err_console
from ..project import find_project_file


def _resolve_app_name(name: str | None) -> str:
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


def _parse_since(since: str) -> int:
    """Parse duration string like '1h', '30m', '5s' to seconds."""
    match = re.match(r"^(\d+)([smh])$", since.strip())
    if not match:
        err_console.print(f"[red]Invalid --since format: '{since}'.[/red] Use e.g. 30s, 5m, 1h")
        raise typer.Exit(1)
    value, unit = int(match.group(1)), match.group(2)
    multiplier = {"s": 1, "m": 60, "h": 3600}
    return value * multiplier[unit]


def logs(
    name: str = typer.Argument(None, help="App name (uses .fp.yaml if omitted)"),
    follow: bool = typer.Option(True, "--follow/--no-follow", "-f/-F", help="Stream logs in real-time"),
    since: str = typer.Option("", "--since", "-s", help="Only logs since (e.g. 30s, 5m, 1h)"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of recent lines"),
):
    """Tail app logs."""
    app_name = _resolve_app_name(name)
    platform = get_active_platform_or_exit()
    client = PlatformClient(platform["url"], platform["token"])

    app = resolve_app(client, app_name)
    app_id = app["app_id"]

    if follow and not since:
        _stream_logs_ws(platform, app_id)
    else:
        _fetch_logs_http(client, app_id, tail, since)


def _fetch_logs_http(client: PlatformClient, app_id: str, tail: int, since: str):
    """Fetch logs via HTTP and print."""
    since_seconds = _parse_since(since) if since else None

    try:
        data = client.get_logs(app_id, tail_lines=tail, since_seconds=since_seconds)
    except PlatformError as e:
        err_console.print(f"[red]Failed to fetch logs:[/red] {e.message}")
        raise typer.Exit(1)

    log_lines = data.get("logs", [])
    if not log_lines:
        console.print("[dim]No logs available.[/dim]")
        return

    for line in log_lines:
        ts = line.get("timestamp", "")
        msg = line.get("message", "")
        if ts:
            console.print(f"[dim]{ts}[/dim] {msg}")
        else:
            console.print(msg)


def _stream_logs_ws(platform: dict, app_id: str):
    """Stream logs via WebSocket."""
    import websockets.sync.client as ws_client

    # Build WebSocket URL from platform URL
    ws_url = platform["url"].replace("https://", "wss://").replace("http://", "ws://")
    url = f"{ws_url}/api/apps/{app_id}/logs/stream?token={platform['token']}"

    console.print(f"[dim]Streaming logs (Ctrl+C to stop)...[/dim]")

    try:
        with ws_client.connect(url) as ws:
            for message in ws:
                try:
                    data = json.loads(message)
                except (json.JSONDecodeError, TypeError):
                    console.print(str(message))
                    continue

                msg_type = data.get("type", "")
                if msg_type == "log":
                    ts = data.get("timestamp", "")
                    msg = data.get("message", "")
                    if ts:
                        console.print(f"[dim]{ts}[/dim] {msg}")
                    else:
                        console.print(msg)
                elif msg_type == "connected":
                    console.print(f"[dim]Connected to pod: {data.get('pod_name', 'unknown')}[/dim]")
                elif msg_type == "status":
                    console.print(f"[yellow]{data.get('message', '')}[/yellow]")
                elif msg_type == "error":
                    err_console.print(f"[red]{data.get('message', '')}[/red]")
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")
    except Exception as e:
        err_console.print(f"[red]WebSocket error:[/red] {e}")
        console.print("[dim]Falling back to HTTP logs...[/dim]")
        # Fallback to HTTP
        from ..api.client import PlatformClient

        client = PlatformClient(platform["url"], platform["token"])
        _fetch_logs_http(client, app_id, 50, "")
