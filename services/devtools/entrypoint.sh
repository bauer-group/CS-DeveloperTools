#!/bin/bash
# =============================================================================
# DevTools Container Entrypoint
# Initialisiert die Umgebung und führt Befehle aus
# =============================================================================

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Git-Konfiguration aus Umgebungsvariablen übernehmen
if [ -n "$GIT_USER_NAME" ]; then
    git config --global user.name "$GIT_USER_NAME"
fi

if [ -n "$GIT_USER_EMAIL" ]; then
    git config --global user.email "$GIT_USER_EMAIL"
fi

# SSH-Key einrichten falls vorhanden
if [ -d "/root/.ssh" ]; then
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/* 2>/dev/null || true
fi

# GPG-Key einrichten falls vorhanden
if [ -d "/root/.gnupg" ]; then
    chmod 700 /root/.gnupg
fi

# Willkommensnachricht nur bei interaktiver Shell
if [ -t 0 ] && [ "$1" = "/bin/bash" ]; then
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              🛠️  DevTools Runtime Container                    ║${NC}"
    echo -e "${GREEN}║         Swiss Army Knife for Git-based Development            ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Git-Status anzeigen falls im Repository
    if git rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH=$(git branch --show-current 2>/dev/null)
        if [ -z "$BRANCH" ]; then
            # Detached HEAD - show short commit hash
            BRANCH="detached @ $(git rev-parse --short HEAD 2>/dev/null)"
        fi
        # Use PROJECT_NAME env var if set, otherwise extract from mount path
        if [ -n "$PROJECT_NAME" ]; then
            REPO="$PROJECT_NAME"
        else
            REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "unknown")
        fi
        echo -e "${CYAN}Repository:${NC} $REPO"
        echo -e "${CYAN}Branch:${NC}     $BRANCH"

        # Kurzer Status (mit Timeout für große Repos)
        if CHANGES=$(timeout 3 git status --porcelain 2>/dev/null | head -100 | wc -l); then
            if [ "$CHANGES" -gt 0 ]; then
                if [ "$CHANGES" -ge 100 ]; then
                    echo -e "${YELLOW}Changes:${NC}    100+ uncommitted file(s)"
                else
                    echo -e "${YELLOW}Changes:${NC}    $CHANGES uncommitted file(s)"
                fi
            else
                echo -e "${GREEN}Changes:${NC}    Working tree clean"
            fi
        else
            echo -e "${YELLOW}Changes:${NC}    (skipped - large repo)"
        fi
        echo ""
    fi

    # Show quick tool summary (first 4 of each category)
    echo -e "${YELLOW}Quick Reference:${NC}"
    echo "  git-stats           - Repository statistics"
    echo "  git-cleanup         - Clean up branches and cache"
    echo "  git-changelog       - Generate changelog from commits"
    echo "  gh-create-repo      - Create GitHub repository"
    echo ""
    echo -e "${YELLOW}Git Aliases:${NC}"
    echo "  git st              - Short status"
    echo "  git lg              - Log graph (20 commits)"
    echo "  git lga             - Full log graph"
    echo "  git branches        - List branches by date"
    echo ""
    echo -e "Type ${CYAN}help-devtools${NC} for full command list (24 tools available)."
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
fi

# Befehl ausführen
exec "$@"
