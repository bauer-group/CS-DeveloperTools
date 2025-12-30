#!/bin/bash
# =============================================================================
# gh-trigger-workflow.sh - GitHub Actions Workflow Trigger
# Löst GitHub Actions Workflows manuell aus
# =============================================================================

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Defaults
REF="main"
WAIT=false
INPUTS=""

usage() {
    echo ""
    echo -e "${BOLD}gh-trigger-workflow.sh${NC} - Trigger GitHub Actions Workflows"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  gh-trigger-workflow.sh <repo> <workflow> [OPTIONS]"
    echo ""
    echo -e "${BOLD}Arguments:${NC}"
    echo "  repo                  Repository (owner/name)"
    echo "  workflow              Workflow file name or ID"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -r, --ref REF         Git ref to run on (default: main)"
    echo "  -i, --input KEY=VAL   Workflow input (can be repeated)"
    echo "  -w, --wait            Wait for workflow to complete"
    echo "  -l, --list            List available workflows"
    echo "  -s, --status          Show recent workflow runs"
    echo "  -h, --help            Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  # List workflows"
    echo "  gh-trigger-workflow.sh myorg/myrepo --list"
    echo ""
    echo "  # Trigger workflow"
    echo "  gh-trigger-workflow.sh myorg/myrepo deploy.yml"
    echo ""
    echo "  # Trigger with inputs"
    echo "  gh-trigger-workflow.sh myorg/myrepo deploy.yml -i env=production -i version=1.2.3"
    echo ""
    echo "  # Trigger on branch and wait"
    echo "  gh-trigger-workflow.sh myorg/myrepo ci.yml -r develop --wait"
    echo ""
    echo "  # Show recent runs"
    echo "  gh-trigger-workflow.sh myorg/myrepo --status"
    echo ""
}

# Check dependencies
check_dependencies() {
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}[ERROR] GitHub CLI (gh) not found${NC}"
        echo "Install from: https://cli.github.com/"
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        echo -e "${RED}[ERROR] Not authenticated with GitHub${NC}"
        echo "Run: gh auth login"
        exit 1
    fi
}

# List workflows
list_workflows() {
    local repo="$1"

    echo ""
    echo -e "${BOLD}Available Workflows:${NC}"
    echo ""

    gh workflow list -R "$repo" --all | while read -r name state id; do
        if [ "$state" = "active" ]; then
            echo -e "  ${GREEN}●${NC} $name"
        else
            echo -e "  ${YELLOW}○${NC} $name ${YELLOW}($state)${NC}"
        fi
    done

    echo ""
}

# Show workflow status
show_status() {
    local repo="$1"

    echo ""
    echo -e "${BOLD}Recent Workflow Runs:${NC}"
    echo ""

    gh run list -R "$repo" --limit 10 | while IFS=$'\t' read -r status conclusion workflow branch event id elapsed date; do
        case "$conclusion" in
            success)
                icon="${GREEN}✓${NC}"
                ;;
            failure)
                icon="${RED}✗${NC}"
                ;;
            cancelled)
                icon="${YELLOW}○${NC}"
                ;;
            in_progress|"")
                icon="${CYAN}⟳${NC}"
                ;;
            *)
                icon="?"
                ;;
        esac

        printf "  %b %-30s %-15s %s\n" "$icon" "$workflow" "$branch" "$date"
    done

    echo ""
}

# Trigger workflow
trigger_workflow() {
    local repo="$1"
    local workflow="$2"
    local ref="$3"
    local inputs="$4"

    echo ""
    echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║                  GitHub Workflow Trigger                      ║${NC}"
    echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${CYAN}Repository:${NC} $repo"
    echo -e "${CYAN}Workflow:${NC} $workflow"
    echo -e "${CYAN}Ref:${NC} $ref"

    if [ -n "$inputs" ]; then
        echo -e "${CYAN}Inputs:${NC}"
        echo "$inputs" | tr ',' '\n' | while read -r input; do
            echo "  - $input"
        done
    fi

    echo ""
    echo -e "${CYAN}Triggering workflow...${NC}"

    # Build command
    CMD="gh workflow run \"$workflow\" -R \"$repo\" --ref \"$ref\""

    if [ -n "$inputs" ]; then
        # Add inputs
        IFS=',' read -ra INPUT_ARRAY <<< "$inputs"
        for input in "${INPUT_ARRAY[@]}"; do
            CMD="$CMD -f \"$input\""
        done
    fi

    # Execute
    if eval "$CMD"; then
        echo -e "${GREEN}✓ Workflow triggered successfully${NC}"
    else
        echo -e "${RED}[ERROR] Failed to trigger workflow${NC}"
        exit 1
    fi

    echo ""
}

# Wait for workflow
wait_for_workflow() {
    local repo="$1"
    local workflow="$2"

    echo -e "${CYAN}Waiting for workflow to complete...${NC}"
    echo ""

    # Get latest run ID
    sleep 2  # Give GitHub a moment to register the run

    RUN_ID=$(gh run list -R "$repo" --workflow "$workflow" --limit 1 --json databaseId -q '.[0].databaseId')

    if [ -z "$RUN_ID" ]; then
        echo -e "${YELLOW}Could not find workflow run${NC}"
        return
    fi

    echo "Run ID: $RUN_ID"
    echo ""

    # Watch the run
    gh run watch "$RUN_ID" -R "$repo"

    # Get final status
    CONCLUSION=$(gh run view "$RUN_ID" -R "$repo" --json conclusion -q '.conclusion')

    echo ""
    case "$CONCLUSION" in
        success)
            echo -e "${GREEN}✓ Workflow completed successfully${NC}"
            ;;
        failure)
            echo -e "${RED}✗ Workflow failed${NC}"
            exit 1
            ;;
        cancelled)
            echo -e "${YELLOW}○ Workflow was cancelled${NC}"
            exit 1
            ;;
        *)
            echo -e "${YELLOW}Workflow ended with: $CONCLUSION${NC}"
            ;;
    esac

    echo ""
}

# Parse arguments
REPO=""
WORKFLOW=""
LIST=false
STATUS=false
INPUT_LIST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--ref)
            REF="$2"
            shift 2
            ;;
        -i|--input)
            if [ -n "$INPUT_LIST" ]; then
                INPUT_LIST="$INPUT_LIST,$2"
            else
                INPUT_LIST="$2"
            fi
            shift 2
            ;;
        -w|--wait)
            WAIT=true
            shift
            ;;
        -l|--list)
            LIST=true
            shift
            ;;
        -s|--status)
            STATUS=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
        *)
            if [ -z "$REPO" ]; then
                REPO="$1"
            elif [ -z "$WORKFLOW" ]; then
                WORKFLOW="$1"
            else
                echo -e "${RED}Unexpected argument: $1${NC}"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate
if [ -z "$REPO" ]; then
    echo -e "${RED}[ERROR] Repository required${NC}"
    usage
    exit 1
fi

# Main
check_dependencies

if [ "$LIST" = true ]; then
    list_workflows "$REPO"
    exit 0
fi

if [ "$STATUS" = true ]; then
    show_status "$REPO"
    exit 0
fi

if [ -z "$WORKFLOW" ]; then
    echo -e "${RED}[ERROR] Workflow name required${NC}"
    echo "Use --list to see available workflows"
    exit 1
fi

trigger_workflow "$REPO" "$WORKFLOW" "$REF" "$INPUT_LIST"

if [ "$WAIT" = true ]; then
    wait_for_workflow "$REPO" "$WORKFLOW"
fi
