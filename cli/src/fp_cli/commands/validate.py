"""fp validate — validate code locally."""

import typer

from ..console import console, err_console
from ..project import read_project, collect_files, detect_mode


def validate():
    """Validate code against platform rules (syntax, imports, security)."""
    # Import vendored validation
    from ..validation import validate_code, validate_multifile

    project = read_project()
    entrypoint = project.get("entrypoint", "app.py")

    files = collect_files(entrypoint=entrypoint)
    mode = detect_mode(files)

    if mode == "multi":
        is_valid, error_msg, error_line, error_file = validate_multifile(files, entrypoint)
        if is_valid:
            console.print(f"[green]Validation passed[/green] ({len(files)} files)")
        else:
            err_console.print(f"[red]Validation failed:[/red] {error_msg}")
            if error_file:
                err_console.print(f"  File: {error_file}")
            if error_line:
                err_console.print(f"  Line: {error_line}")
            raise typer.Exit(1)
    else:
        code = files[entrypoint]
        is_valid, error_msg, error_line = validate_code(code)
        if is_valid:
            console.print("[green]Validation passed[/green]")
        else:
            err_console.print(f"[red]Validation failed:[/red] {error_msg}")
            if error_line:
                err_console.print(f"  Line: {error_line}")
            raise typer.Exit(1)
