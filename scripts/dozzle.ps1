# Dozzle Container Monitor Management Script
# Usage: .\dozzle.ps1 <command>
# Commands: start, stop, restart, status, logs, pull, open

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "pull", "open", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

function Get-DozzlePort {
    if (Test-Path .env) {
        $match = Select-String -Path .env -Pattern 'DOZZLE_PORT=(\d+)' -ErrorAction SilentlyContinue
        if ($match) { return $match.Matches.Groups[1].Value }
    }
    return "9999"
}

switch ($Command) {
    "start" {
        docker compose up -d
        $port = Get-DozzlePort
        Write-Host "Dozzle started at http://localhost:$port" -ForegroundColor Green
    }
    "stop" {
        docker compose down
        Write-Host "Dozzle stopped" -ForegroundColor Yellow
    }
    "restart" {
        docker compose restart
        Write-Host "Dozzle restarted" -ForegroundColor Green
    }
    "status" {
        docker compose ps
    }
    "logs" {
        docker compose logs -f
    }
    "pull" {
        docker compose pull
        Write-Host "Dozzle image updated" -ForegroundColor Green
    }
    "open" {
        $port = Get-DozzlePort
        Start-Process "http://localhost:$port"
    }
    "help" {
        Write-Host @"
Dozzle Container Monitor

Usage: .\dozzle.ps1 <command>

Commands:
  start     Start Dozzle container
  stop      Stop and remove container
  restart   Restart container
  status    Show container status
  logs      Follow container logs
  pull      Pull latest image
  open      Open web UI in browser
  help      Show this help message
"@
    }
}
