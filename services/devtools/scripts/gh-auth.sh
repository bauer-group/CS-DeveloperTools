#!/bin/bash
# @name: gh-auth
# @description: Manage GitHub CLI authentication (persistent)
# @category: github
# @usage: gh-auth.sh [login|logout|status|switch]
# =============================================================================
# gh-auth.sh - GitHub Authentication Manager
# Manages persistent GitHub CLI authentication stored in /data
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Data directory (mounted from host)
DATA_DIR="/data"
GH_CONFIG_DIR="$DATA_DIR/gh"

usage() {
    echo ""
    echo -e "${BOLD}gh-auth.sh${NC} - GitHub Authentication Manager"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  gh-auth.sh <command> [OPTIONS]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo "  login           Login to GitHub (interactive)"
    echo "  login-token     Login with a Personal Access Token"
    echo "  logout          Logout from GitHub"
    echo "  status          Show current authentication status"
    echo "  switch          Switch between GitHub accounts"
    echo "  token           Display current token (for debugging)"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -h, --help      Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  gh-auth.sh login              # Interactive login (browser)"
    echo "  gh-auth.sh login-token        # Login with PAT"
    echo "  gh-auth.sh status             # Check auth status"
    echo "  gh-auth.sh logout             # Remove credentials"
    echo ""
    echo -e "${BOLD}Note:${NC}"
    echo "  Credentials are stored in /data/gh (mounted from host .data/)"
    echo "  and persist across container restarts."
    echo ""
}

# Ensure data directory exists
ensure_data_dir() {
    if [ ! -d "$DATA_DIR" ]; then
        echo -e "${RED}[ERROR] Data directory not mounted${NC}"
        echo "Make sure to start the container with the .data volume mounted."
        exit 1
    fi

    mkdir -p "$GH_CONFIG_DIR"
    export GH_CONFIG_DIR
}

# Login interactively
do_login() {
    echo ""
    echo -e "${BOLD}${CYAN}GitHub Login${NC}"
    echo ""

    echo -e "${YELLOW}Starting interactive login...${NC}"
    echo "You will be prompted to authenticate via browser or device code."
    echo ""

    gh auth login --git-protocol https

    echo ""
    echo -e "${GREEN}Login successful!${NC}"
    show_status
}

# Login with token
do_login_token() {
    echo ""
    echo -e "${BOLD}${CYAN}GitHub Login with Token${NC}"
    echo ""

    echo -e "Enter your Personal Access Token (PAT):"
    echo -e "${YELLOW}(Create one at: https://github.com/settings/tokens)${NC}"
    echo ""
    echo "Required scopes: repo, read:org, workflow"
    echo ""

    read -rsp "Token: " TOKEN
    echo ""

    if [ -z "$TOKEN" ]; then
        echo -e "${RED}[ERROR] No token provided${NC}"
        exit 1
    fi

    echo "$TOKEN" | gh auth login --with-token

    echo ""
    echo -e "${GREEN}Login successful!${NC}"
    show_status
}

# Logout
do_logout() {
    echo ""
    echo -e "${BOLD}${CYAN}GitHub Logout${NC}"
    echo ""

    if gh auth status &>/dev/null; then
        gh auth logout
        echo -e "${GREEN}Logged out successfully${NC}"
    else
        echo -e "${YELLOW}Not currently logged in${NC}"
    fi

    echo ""
}

# Show status
show_status() {
    echo ""
    echo -e "${BOLD}${CYAN}GitHub Authentication Status${NC}"
    echo ""

    if gh auth status 2>&1; then
        echo ""
        echo -e "${CYAN}Logged in user:${NC}"
        gh api user --jq '.login + " (" + .name + ")"' 2>/dev/null || echo "  (unable to fetch user info)"

        echo ""
        echo -e "${CYAN}Config location:${NC} $GH_CONFIG_DIR"
    fi

    echo ""
}

# Switch accounts
do_switch() {
    echo ""
    echo -e "${BOLD}${CYAN}Switch GitHub Account${NC}"
    echo ""

    # Show current accounts
    echo -e "${CYAN}Current accounts:${NC}"
    gh auth status 2>&1 | grep -E "Logged in|account" || echo "  No accounts found"
    echo ""

    echo "To switch accounts:"
    echo "  1. Run: gh-auth.sh logout"
    echo "  2. Run: gh-auth.sh login"
    echo ""
}

# Show token (for debugging)
show_token() {
    echo ""
    echo -e "${BOLD}${CYAN}GitHub Token${NC}"
    echo ""

    if gh auth status &>/dev/null; then
        echo -e "${YELLOW}WARNING: This displays your authentication token!${NC}"
        read -rp "Continue? (y/N): " CONFIRM

        if [[ "$CONFIRM" =~ ^[yY]$ ]]; then
            gh auth token
        fi
    else
        echo -e "${RED}Not logged in${NC}"
    fi

    echo ""
}

# Parse arguments
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        login)
            COMMAND="login"
            shift
            ;;
        login-token)
            COMMAND="login-token"
            shift
            ;;
        logout)
            COMMAND="logout"
            shift
            ;;
        status)
            COMMAND="status"
            shift
            ;;
        switch)
            COMMAND="switch"
            shift
            ;;
        token)
            COMMAND="token"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Default to status if no command
if [ -z "$COMMAND" ]; then
    COMMAND="status"
fi

# Setup
ensure_data_dir

# Execute command
case $COMMAND in
    login)
        do_login
        ;;
    login-token)
        do_login_token
        ;;
    logout)
        do_logout
        ;;
    status)
        show_status
        ;;
    switch)
        do_switch
        ;;
    token)
        show_token
        ;;
esac
