#!/bin/bash
# Dozzle Container Monitor Management Script
# Usage: ./dozzle.sh <command>
# Commands: start, stop, restart, status, logs, pull, open

set -e
cd "$(dirname "$0")/.."

get_port() {
    if [[ -f .env ]]; then
        # POSIX-compatible (works on macOS and Linux)
        grep '^DOZZLE_PORT=' .env 2>/dev/null | cut -d'=' -f2 || echo "9999"
    else
        echo "9999"
    fi
}

open_browser() {
    local url
    url="http://localhost:$(get_port)"
    case "$(uname -s)" in
        Darwin)  open "$url" ;;
        Linux)   xdg-open "$url" 2>/dev/null || echo "Open: $url" ;;
        *)       echo "Open: $url" ;;
    esac
}

case "${1:-help}" in
    start)
        docker compose up -d
        echo -e "\033[32mDozzle started at http://localhost:$(get_port)\033[0m"
        ;;
    stop)
        docker compose down
        echo -e "\033[33mDozzle stopped\033[0m"
        ;;
    restart)
        docker compose restart
        echo -e "\033[32mDozzle restarted\033[0m"
        ;;
    status)
        docker compose ps
        ;;
    logs)
        docker compose logs -f
        ;;
    pull)
        docker compose pull
        echo -e "\033[32mDozzle image updated\033[0m"
        ;;
    open)
        open_browser
        ;;
    help|*)
        cat <<EOF
Dozzle Container Monitor

Usage: ./dozzle.sh <command>

Commands:
  start     Start Dozzle container
  stop      Stop and remove container
  restart   Restart container
  status    Show container status
  logs      Follow container logs
  pull      Pull latest image
  open      Open web UI in browser
  help      Show this help message
EOF
        ;;
esac
