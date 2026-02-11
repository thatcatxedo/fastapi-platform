"""Platform configuration stored in ~/.fp/config.toml"""

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

CONFIG_DIR = Path.home() / ".fp"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def _read_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return tomllib.loads(CONFIG_FILE.read_text())


def _write_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = _serialize_toml(config)
    CONFIG_FILE.write_text(lines)
    CONFIG_FILE.chmod(0o600)


def _serialize_toml(data: dict, prefix: str = "") -> str:
    """Minimal TOML serializer for flat/nested string tables."""
    lines = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            lines.append(f"[{full_key}]")
            for k, v in value.items():
                if isinstance(v, dict):
                    lines.append("")
                    lines.append(f"[{full_key}.{k}]")
                    for k2, v2 in v.items():
                        lines.append(f'{k2} = "{v2}"')
                else:
                    lines.append(f'{k} = "{v}"')
            lines.append("")
        else:
            lines.append(f'{key} = "{value}"')
    return "\n".join(lines) + "\n"


def save_platform(name: str, url: str, token: str, username: str) -> None:
    config = _read_config()
    platforms = config.get("platforms", {})
    platforms[name] = {"url": url, "token": token, "username": username}
    config["platforms"] = platforms
    config["active"] = {"platform": name}
    _write_config(config)


def remove_platform(name: str) -> bool:
    config = _read_config()
    platforms = config.get("platforms", {})
    if name not in platforms:
        return False
    del platforms[name]
    config["platforms"] = platforms
    active = config.get("active", {})
    if active.get("platform") == name:
        # Switch to first remaining platform or clear
        remaining = list(platforms.keys())
        if remaining:
            active["platform"] = remaining[0]
        else:
            config.pop("active", None)
    _write_config(config)
    return True


def get_active_platform() -> dict | None:
    """Return {url, token, username} for the active platform, or None."""
    config = _read_config()
    active_name = config.get("active", {}).get("platform")
    if not active_name:
        return None
    platforms = config.get("platforms", {})
    platform = platforms.get(active_name)
    if not platform:
        return None
    return {**platform, "name": active_name}


def get_active_platform_or_exit():
    """Return active platform config or print error and exit."""
    from .console import err_console

    platform = get_active_platform()
    if not platform:
        err_console.print(
            "[red]Not authenticated.[/red] Run [bold]fp auth <platform-url>[/bold] first."
        )
        raise SystemExit(1)
    return platform
