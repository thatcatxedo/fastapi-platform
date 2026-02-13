# fp — Go CLI for FastAPI Platform

A Go implementation of the fp CLI for the FastAPI Platform. Single binary, no Python required.

## Compatibility

- **Config:** Uses the same `~/.fp/config.toml` as the Python CLI. You can switch between `fp` (Python) and `fp` (Go) after authenticating with either.
- **Projects:** Same `.fp.yaml` format. Projects created with one CLI work with the other.

## Build

```bash
go build -o fp .
```

## Cross-compile

```bash
# macOS ARM (M1/M2/M3)
GOOS=darwin GOARCH=arm64 go build -o fp-darwin-arm64 .

# macOS Intel
GOOS=darwin GOARCH=amd64 go build -o fp-darwin-amd64 .

# Linux
GOOS=linux GOARCH=amd64 go build -o fp-linux-amd64 .

# Windows
GOOS=windows GOARCH=amd64 go build -o fp-windows-amd64.exe .
```

## Version

```bash
go build -ldflags "-X main.Version=v0.1.0" -o fp .
```

## Commands

| Command | Description |
|---------|-------------|
| `fp auth login <url>` | Authenticate with platform |
| `fp auth whoami` | Show current user |
| `fp auth logout` | Remove credentials |
| `fp init` | Scaffold new project |
| `fp deploy` | Deploy to platform |
| `fp list` | List apps |
| `fp status` | Show app status |
| `fp open` | Open app in browser |
| `fp delete <name>` | Delete an app |
| `fp logs [name]` | Tail logs (WebSocket or HTTP) |
| `fp dev` | Run locally with uvicorn |
| `fp pull <name>` | Pull app code |
| `fp push` | Push draft (no deploy) |
| `fp version` | Show version |

## Skipped

- `fp validate` — Not implemented. Server-side validation runs on deploy.
