# Developer Monitor

Real-time Docker container log viewer and management tool for developers using Docker Desktop.

Based on [Dozzle](https://dozzle.dev) - a lightweight, web-based Docker log viewer.

## Features

- **Real-time log streaming** - View container logs as they happen
- **Container management** - Start, stop, and restart containers from the UI
- **Shell access** - Execute commands directly in containers
- **SQL queries** - Query JSON logs using SQL syntax (DuckDB in browser)
- **Multi-container view** - Monitor multiple containers simultaneously
- **Search & filter** - Find specific log entries quickly
- **Dark/Light mode** - Comfortable viewing in any environment

## Quick Start

### 1. Configure

```bash
cp .env.example .env
```

Edit `.env` to customize settings (optional).

### 2. Start

**Windows (PowerShell):**

```powershell
.\scripts\dozzle.ps1 start
```

**Linux/macOS:**

```bash
chmod +x scripts/dozzle.sh
./scripts/dozzle.sh start
```

**Or directly with Docker Compose:**

```bash
docker compose up -d
```

### 3. Access

Open [http://localhost:9999](http://localhost:9999) in your browser.

## Scripts

Management scripts are available for Windows and Linux/macOS:

| Command   | Description               |
| --------- | ------------------------- |
| `start`   | Start Dozzle container    |
| `stop`    | Stop and remove container |
| `restart` | Restart container         |
| `status`  | Show container status     |
| `logs`    | Follow container logs     |
| `pull`    | Pull latest image         |
| `open`    | Open web UI in browser    |
| `help`    | Show available commands   |

**Windows:**

```powershell
.\scripts\dozzle.ps1 <command>
```

**Linux/macOS:**

```bash
./scripts/dozzle.sh <command>
```

## Configuration

All settings are configured via environment variables in `.env`:

| Variable                | Default     | Description             |
| ----------------------- | ----------- | ----------------------- |
| `DOZZLE_PORT`           | `9999`      | Web UI port             |
| `DOZZLE_HOSTNAME`       | `localhost` | Display name in UI      |
| `DOZZLE_ENABLE_ACTIONS` | `true`      | Allow start/stop/restart |
| `DOZZLE_ENABLE_SHELL`   | `true`      | Allow shell access      |
| `DOZZLE_NO_ANALYTICS`   | `true`      | Disable usage tracking  |
| `DOZZLE_AUTH_PROVIDER`  | `none`      | Authentication mode     |

See [.env.example](.env.example) for all options.

## Authentication (Optional)

To enable user authentication:

1. Generate a password hash:

   ```bash
   docker run -it --rm amir20/dozzle generate admin --password YourPassword --email admin@example.com
   ```

2. Copy and edit the users file:

   ```bash
   cp data/users.yml.example data/users.yml
   # Add the generated hash to users.yml
   ```

3. Enable authentication in `.env`:

   ```bash
   DOZZLE_AUTH_PROVIDER=simple
   ```

4. Uncomment the data volume in `docker-compose.yml`

## Requirements

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose v2+

## Documentation

- [Dozzle Documentation](https://dozzle.dev)
- [Container Actions](https://dozzle.dev/guide/actions)
- [Shell Access](https://dozzle.dev/guide/shell)
- [Authentication](https://dozzle.dev/guide/authentication)

## License

MIT
