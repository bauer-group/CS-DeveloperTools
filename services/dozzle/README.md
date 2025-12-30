# Dozzle - Container Monitor

Real-time Docker container log viewer and management tool.

Based on [Dozzle](https://dozzle.dev) - a lightweight, web-based Docker log viewer.

## Features

- **Real-time log streaming** - View container logs as they happen
- **Container management** - Start, stop, and restart containers from the UI
- **Shell access** - Execute commands directly in containers
- **SQL queries** - Query JSON logs using SQL syntax (DuckDB)
- **Multi-container view** - Monitor multiple containers simultaneously
- **Search & filter** - Find specific log entries quickly

## Quick Start

```bash
# Configure (optional)
cp .env.example .env

# Start
./scripts/dozzle.sh start

# Open browser
./scripts/dozzle.sh open
```

Or with PowerShell:
```powershell
.\scripts\dozzle.ps1 start
.\scripts\dozzle.ps1 open
```

## Commands

| Command   | Description               |
|-----------|---------------------------|
| `start`   | Start Dozzle container    |
| `stop`    | Stop and remove container |
| `restart` | Restart container         |
| `status`  | Show container status     |
| `logs`    | Follow container logs     |
| `pull`    | Pull latest image         |
| `open`    | Open web UI in browser    |

## Configuration

Edit `.env` to customize settings:

| Variable                | Default     | Description              |
|-------------------------|-------------|--------------------------|
| `DOZZLE_PORT`           | `9999`      | Web UI port              |
| `DOZZLE_HOSTNAME`       | `localhost` | Display name in UI       |
| `DOZZLE_ENABLE_ACTIONS` | `true`      | Allow start/stop/restart |
| `DOZZLE_ENABLE_SHELL`   | `true`      | Allow shell access       |
| `DOZZLE_AUTH_PROVIDER`  | `none`      | Authentication mode      |

## Authentication (Optional)

1. Generate password hash:
   ```bash
   docker run -it --rm amir20/dozzle generate admin --password YourPassword
   ```

2. Copy and edit users file:
   ```bash
   cp data/users.yml.example data/users.yml
   ```

3. Enable in `.env`:
   ```bash
   DOZZLE_AUTH_PROVIDER=simple
   ```

4. Uncomment data volume in `docker-compose.yml`

## Documentation

- [Dozzle Documentation](https://dozzle.dev)
- [Container Actions](https://dozzle.dev/guide/actions)
- [Authentication](https://dozzle.dev/guide/authentication)
