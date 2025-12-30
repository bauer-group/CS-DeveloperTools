#!/bin/bash
# =============================================================================
# gh-create-repo.sh - Create GitHub Repository
# Erstellt ein neues GitHub Repository mit konfigurierbaren Einstellungen
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
VISIBILITY="private"
INIT_README=false
ADD_GITIGNORE=""
ADD_LICENSE=""
DESCRIPTION=""
HOMEPAGE=""
TOPICS=""
CLONE_AFTER=false
DRY_RUN=false

usage() {
    echo ""
    echo -e "${BOLD}gh-create-repo.sh${NC} - Create GitHub Repository"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  gh-create-repo.sh <name> [OPTIONS]"
    echo "  gh-create-repo.sh -o <org> <name> [OPTIONS]"
    echo ""
    echo -e "${BOLD}Arguments:${NC}"
    echo "  name                  Repository name"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -o, --org ORG         Create in organization (default: personal)"
    echo "  -d, --description     Repository description"
    echo "  -h, --homepage URL    Homepage URL"
    echo "  -t, --topics TOPICS   Comma-separated topics"
    echo "  --public              Create public repository (default: private)"
    echo "  --internal            Create internal repository (Enterprise only)"
    echo "  --init                Initialize with README"
    echo "  --gitignore LANG      Add .gitignore template (e.g., Python, Node)"
    echo "  --license LICENSE     Add license (e.g., MIT, Apache-2.0)"
    echo "  --clone               Clone repository after creation"
    echo "  --dry-run             Show what would be created"
    echo "  --help                Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  # Create private repo"
    echo "  gh-create-repo.sh my-project"
    echo ""
    echo "  # Create public repo with description"
    echo "  gh-create-repo.sh my-project --public -d 'My awesome project'"
    echo ""
    echo "  # Create in organization with topics"
    echo "  gh-create-repo.sh -o myorg my-project -t 'python,cli,tool'"
    echo ""
    echo "  # Full setup"
    echo "  gh-create-repo.sh my-project --public --init \\"
    echo "    --gitignore Python --license MIT \\"
    echo "    -d 'Description' -t 'python,api' --clone"
    echo ""
}

# Check dependencies
check_dependencies() {
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}[ERROR] GitHub CLI (gh) not found${NC}"
        echo "Install from: https://cli.github.com/"
        exit 1
    fi

    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        echo -e "${RED}[ERROR] Not authenticated with GitHub${NC}"
        echo "Run: gh auth login"
        exit 1
    fi
}

# Parse arguments
REPO_NAME=""
ORG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--org)
            ORG="$2"
            shift 2
            ;;
        -d|--description)
            DESCRIPTION="$2"
            shift 2
            ;;
        -h|--homepage)
            HOMEPAGE="$2"
            shift 2
            ;;
        -t|--topics)
            TOPICS="$2"
            shift 2
            ;;
        --public)
            VISIBILITY="public"
            shift
            ;;
        --internal)
            VISIBILITY="internal"
            shift
            ;;
        --init)
            INIT_README=true
            shift
            ;;
        --gitignore)
            ADD_GITIGNORE="$2"
            shift 2
            ;;
        --license)
            ADD_LICENSE="$2"
            shift 2
            ;;
        --clone)
            CLONE_AFTER=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        -*)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
        *)
            if [ -z "$REPO_NAME" ]; then
                REPO_NAME="$1"
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
if [ -z "$REPO_NAME" ]; then
    echo -e "${RED}[ERROR] Repository name required${NC}"
    usage
    exit 1
fi

# Main
check_dependencies

echo ""
echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                  GitHub Repository Creator                    ║${NC}"
echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Determine full repo name
if [ -n "$ORG" ]; then
    FULL_NAME="$ORG/$REPO_NAME"
else
    FULL_NAME="$REPO_NAME"
fi

echo -e "${CYAN}Repository:${NC} $FULL_NAME"
echo -e "${CYAN}Visibility:${NC} $VISIBILITY"
[ -n "$DESCRIPTION" ] && echo -e "${CYAN}Description:${NC} $DESCRIPTION"
[ -n "$HOMEPAGE" ] && echo -e "${CYAN}Homepage:${NC} $HOMEPAGE"
[ -n "$TOPICS" ] && echo -e "${CYAN}Topics:${NC} $TOPICS"
[ "$INIT_README" = true ] && echo -e "${CYAN}Initialize:${NC} Yes (with README)"
[ -n "$ADD_GITIGNORE" ] && echo -e "${CYAN}Gitignore:${NC} $ADD_GITIGNORE"
[ -n "$ADD_LICENSE" ] && echo -e "${CYAN}License:${NC} $ADD_LICENSE"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN - No changes will be made${NC}"
    echo ""
    echo "Would execute:"
    echo ""

    CMD="gh repo create $FULL_NAME --$VISIBILITY"
    [ -n "$DESCRIPTION" ] && CMD="$CMD --description \"$DESCRIPTION\""
    [ -n "$HOMEPAGE" ] && CMD="$CMD --homepage \"$HOMEPAGE\""
    [ "$INIT_README" = true ] && CMD="$CMD --add-readme"
    [ -n "$ADD_GITIGNORE" ] && CMD="$CMD --gitignore \"$ADD_GITIGNORE\""
    [ -n "$ADD_LICENSE" ] && CMD="$CMD --license \"$ADD_LICENSE\""

    echo "  $CMD"

    if [ -n "$TOPICS" ]; then
        echo "  gh repo edit $FULL_NAME --add-topic \"$TOPICS\""
    fi

    if [ "$CLONE_AFTER" = true ]; then
        echo "  gh repo clone $FULL_NAME"
    fi

    exit 0
fi

# Build command
CMD_ARGS=("repo" "create" "$FULL_NAME" "--$VISIBILITY")

[ -n "$DESCRIPTION" ] && CMD_ARGS+=("--description" "$DESCRIPTION")
[ -n "$HOMEPAGE" ] && CMD_ARGS+=("--homepage" "$HOMEPAGE")
[ "$INIT_README" = true ] && CMD_ARGS+=("--add-readme")
[ -n "$ADD_GITIGNORE" ] && CMD_ARGS+=("--gitignore" "$ADD_GITIGNORE")
[ -n "$ADD_LICENSE" ] && CMD_ARGS+=("--license" "$ADD_LICENSE")

# Create repository
echo -e "${CYAN}Creating repository...${NC}"
if gh "${CMD_ARGS[@]}"; then
    echo -e "${GREEN}✓ Repository created${NC}"
else
    echo -e "${RED}[ERROR] Failed to create repository${NC}"
    exit 1
fi

# Add topics if specified
if [ -n "$TOPICS" ]; then
    echo ""
    echo -e "${CYAN}Adding topics...${NC}"

    # Convert comma-separated to multiple --add-topic flags
    IFS=',' read -ra TOPIC_ARRAY <<< "$TOPICS"
    for topic in "${TOPIC_ARRAY[@]}"; do
        topic=$(echo "$topic" | xargs)  # trim whitespace
        if [ -n "$topic" ]; then
            gh repo edit "$FULL_NAME" --add-topic "$topic" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}✓ Topics added${NC}"
fi

# Get repo URL
REPO_URL=$(gh repo view "$FULL_NAME" --json url -q '.url')

echo ""
echo -e "${GREEN}✓ Repository ready${NC}"
echo ""
echo -e "${CYAN}URL:${NC} $REPO_URL"

# Clone if requested
if [ "$CLONE_AFTER" = true ]; then
    echo ""
    echo -e "${CYAN}Cloning repository...${NC}"
    gh repo clone "$FULL_NAME"
    echo -e "${GREEN}✓ Repository cloned to ./$REPO_NAME${NC}"
fi

echo ""
echo -e "${BOLD}Next steps:${NC}"
if [ "$CLONE_AFTER" = true ]; then
    echo "  cd $REPO_NAME"
    echo "  # Start coding!"
else
    echo "  gh repo clone $FULL_NAME"
    echo "  # Or clone with: git clone $REPO_URL"
fi
echo ""
