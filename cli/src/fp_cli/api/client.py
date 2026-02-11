"""HTTP client for the FastAPI Platform API."""

import httpx


class PlatformError(Exception):
    """Error from the platform API."""

    def __init__(self, message: str, status_code: int = 0, code: str = ""):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def _parse_error(response: httpx.Response) -> PlatformError:
    """Parse an error response into a PlatformError."""
    try:
        data = response.json()
    except Exception:
        return PlatformError(
            f"HTTP {response.status_code}: {response.text}",
            status_code=response.status_code,
        )

    detail = data.get("detail", data)
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
        code = detail.get("code", "")
    elif isinstance(detail, str):
        message = detail
        code = ""
    else:
        message = str(data)
        code = ""

    return PlatformError(message, status_code=response.status_code, code=code)


class PlatformClient:
    """Client for the FastAPI Platform API."""

    def __init__(self, base_url: str, token: str = ""):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        response = self._client.request(method, path, **kwargs)
        if not response.is_success:
            raise _parse_error(response)
        if response.status_code == 204:
            return {}
        return response.json()

    # --- Auth ---

    def login(self, username: str, password: str) -> dict:
        """Login and return token response."""
        return self._request(
            "POST",
            "/api/auth/login",
            json={"username": username, "password": password},
        )

    def me(self) -> dict:
        """Get current user info."""
        return self._request("GET", "/api/auth/me")

    # --- Apps ---

    def list_apps(self) -> list[dict]:
        return self._request("GET", "/api/apps")

    def get_app(self, app_id: str) -> dict:
        return self._request("GET", f"/api/apps/{app_id}")

    def create_app(self, payload: dict) -> dict:
        return self._request("POST", "/api/apps", json=payload)

    def update_app(self, app_id: str, payload: dict) -> dict:
        return self._request("PUT", f"/api/apps/{app_id}", json=payload)

    def delete_app(self, app_id: str) -> dict:
        return self._request("DELETE", f"/api/apps/{app_id}")

    def save_draft(self, app_id: str, payload: dict) -> dict:
        return self._request("PUT", f"/api/apps/{app_id}/draft", json=payload)

    def deploy_status(self, app_id: str) -> dict:
        return self._request("GET", f"/api/apps/{app_id}/deploy-status")

    def get_events(self, app_id: str, limit: int = 50) -> dict:
        return self._request(
            "GET", f"/api/apps/{app_id}/events", params={"limit": limit}
        )

    def get_logs(
        self, app_id: str, tail_lines: int = 100, since_seconds: int | None = None
    ) -> dict:
        params: dict = {"tail_lines": tail_lines}
        if since_seconds is not None:
            params["since_seconds"] = since_seconds
        return self._request("GET", f"/api/apps/{app_id}/logs", params=params)

    def validate_code(self, payload: dict) -> dict:
        return self._request("POST", "/api/apps/validate", json=payload)

    # --- Templates ---

    def list_templates(self) -> list[dict]:
        return self._request("GET", "/api/templates")

    # --- Databases ---

    def list_databases(self) -> dict:
        return self._request("GET", "/api/databases")


def resolve_app(client: PlatformClient, name: str) -> dict:
    """Find an app by name. Returns the app dict or exits with error."""
    from ..console import err_console

    apps = client.list_apps()
    matches = [a for a in apps if a["name"] == name]
    if not matches:
        err_console.print(f"[red]No app named '{name}' found.[/red]")
        err_console.print("Run [bold]fp list[/bold] to see your apps.")
        raise SystemExit(1)
    return matches[0]
