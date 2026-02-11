"""Project manifest (.fp.yaml) read/write."""

from pathlib import Path

import yaml

PROJECT_FILE = ".fp.yaml"

ALLOWED_EXTENSIONS = {".py", ".css", ".js", ".svg", ".html", ".json", ".txt"}


def find_project_file(start: Path | None = None) -> Path | None:
    """Find .fp.yaml in current or parent directories."""
    current = start or Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / PROJECT_FILE
        if candidate.exists():
            return candidate
    return None


def read_project(path: Path | None = None) -> dict:
    """Read and return project config. Exits if not found."""
    fp_file = path or find_project_file()
    if not fp_file or not fp_file.exists():
        from .console import err_console

        err_console.print(
            f"[red]No {PROJECT_FILE} found.[/red] Run [bold]fp init[/bold] first."
        )
        raise SystemExit(1)
    return yaml.safe_load(fp_file.read_text()) or {}


def write_project(data: dict, directory: Path | None = None) -> Path:
    """Write project config to .fp.yaml. Returns the file path."""
    target = (directory or Path.cwd()) / PROJECT_FILE
    target.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return target


def collect_files(directory: Path | None = None, entrypoint: str = "app.py") -> dict[str, str]:
    """Collect all deployable files from directory."""
    root = directory or Path.cwd()
    files = {}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in ALLOWED_EXTENSIONS:
            continue

        rel = str(path.relative_to(root))

        # Skip hidden files, __pycache__, .venv, node_modules, etc.
        parts = Path(rel).parts
        if any(p.startswith(".") or p == "__pycache__" or p == ".venv" or p == "node_modules" for p in parts):
            continue

        files[rel] = path.read_text()

    if entrypoint not in files:
        from .console import err_console

        err_console.print(f"[red]Entrypoint '{entrypoint}' not found in {root}[/red]")
        raise SystemExit(1)

    return files


def detect_mode(files: dict[str, str]) -> str:
    """Detect single vs multi mode from collected files."""
    py_files = [f for f in files if f.endswith(".py")]
    return "multi" if len(py_files) > 1 or any(f for f in files if not f.endswith(".py")) else "single"
