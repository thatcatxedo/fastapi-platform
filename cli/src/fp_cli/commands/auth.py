"""Authentication commands: fp auth, fp whoami, fp logout"""

import typer
from rich.prompt import Prompt

from ..api.client import PlatformClient, PlatformError
from ..config import save_platform, remove_platform, get_active_platform
from ..console import console, err_console

app = typer.Typer(help="Authentication commands")


@app.command()
def login(
    platform_url: str = typer.Argument(help="Platform URL (e.g. https://platform.gatorlunch.com)"),
    token: str = typer.Option("", "--token", "-t", help="API token for CI/headless auth"),
    name: str = typer.Option("default", "--name", "-n", help="Name for this platform config"),
):
    """Authenticate with a FastAPI Platform deployment."""
    url = platform_url.rstrip("/")
    if not url.startswith("http"):
        url = f"https://{url}"

    if token:
        # Token-based auth (CI/headless)
        client = PlatformClient(url, token)
        try:
            user = client.me()
        except PlatformError as e:
            err_console.print(f"[red]Authentication failed:[/red] {e.message}")
            raise typer.Exit(1)

        save_platform(name, url, token, user["username"])
        console.print(
            f"Authenticated as [bold]{user['username']}[/bold] on {url}"
        )
        return

    # Interactive login
    console.print(f"Logging in to [bold]{url}[/bold]")
    username = Prompt.ask("Username")
    password = Prompt.ask("Password", password=True)

    client = PlatformClient(url)
    try:
        result = client.login(username, password)
    except PlatformError as e:
        err_console.print(f"[red]Login failed:[/red] {e.message}")
        raise typer.Exit(1)

    access_token = result["access_token"]

    # Verify the token works
    client = PlatformClient(url, access_token)
    try:
        user = client.me()
    except PlatformError as e:
        err_console.print(f"[red]Token verification failed:[/red] {e.message}")
        raise typer.Exit(1)

    save_platform(name, url, access_token, user["username"])
    console.print(
        f"Authenticated as [bold]{user['username']}[/bold] on {url}"
    )


@app.command()
def whoami():
    """Show current authentication status."""
    platform = get_active_platform()
    if not platform:
        err_console.print(
            "[red]Not authenticated.[/red] Run [bold]fp auth login <platform-url>[/bold] first."
        )
        raise typer.Exit(1)

    client = PlatformClient(platform["url"], platform["token"])
    try:
        user = client.me()
    except PlatformError as e:
        err_console.print(f"[red]Token expired or invalid:[/red] {e.message}")
        err_console.print("Run [bold]fp auth login <platform-url>[/bold] to re-authenticate.")
        raise typer.Exit(1)

    console.print(f"  User:     [bold]{user['username']}[/bold]")
    console.print(f"  Email:    {user.get('email', 'n/a')}")
    console.print(f"  Platform: {platform['url']}")
    console.print(f"  Config:   {platform['name']}")
    if user.get("is_admin"):
        console.print("  Role:     [yellow]admin[/yellow]")


@app.command()
def logout(
    name: str = typer.Option("", "--name", "-n", help="Platform config name to remove (default: active)"),
):
    """Remove stored credentials."""
    if not name:
        platform = get_active_platform()
        if not platform:
            err_console.print("[yellow]No active platform to log out from.[/yellow]")
            raise typer.Exit(0)
        name = platform["name"]

    if remove_platform(name):
        console.print(f"Logged out from [bold]{name}[/bold]")
    else:
        err_console.print(f"[yellow]No platform config named '{name}' found.[/yellow]")
