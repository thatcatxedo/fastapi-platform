"""fp dev — run locally with hot reload."""

import os
import subprocess
import sys

import typer

from ..console import console, err_console
from ..project import read_project


def dev(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run on"),
):
    """Run the app locally with hot reload."""
    project = read_project()
    entrypoint = project.get("entrypoint", "app.py")

    # Derive module path: app.py -> app:app, src/app.py -> src.app:app
    module = entrypoint.replace("/", ".").removesuffix(".py")
    app_ref = f"{module}:app"

    # Set up environment
    env = os.environ.copy()

    # Inject PLATFORM_MONGO_URI if database is enabled
    if project.get("database"):
        mongo_uri = env.get("PLATFORM_MONGO_URI", "mongodb://localhost:27017")
        env["PLATFORM_MONGO_URI"] = mongo_uri
        console.print(f"  PLATFORM_MONGO_URI={mongo_uri}")

    # Resolve env vars from .fp.yaml
    project_env = project.get("env")
    if project_env and isinstance(project_env, dict):
        for key, value in project_env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                env[key] = os.environ.get(env_name, "")
            else:
                env[key] = str(value)

    console.print(f"Running [bold]{app_ref}[/bold] on port {port}")
    console.print("[dim]Ctrl+C to stop[/dim]")
    console.print()

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                app_ref,
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
            ],
            env=env,
        )
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        err_console.print(
            "[red]uvicorn not found.[/red] Install it: [bold]pip install uvicorn[/bold]"
        )
        raise typer.Exit(1)
