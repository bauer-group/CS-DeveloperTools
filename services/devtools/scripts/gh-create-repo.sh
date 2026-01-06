#!/bin/bash
# @name: gh-create-repo
# @description: Create a new GitHub repository with full configuration
# @category: github
# @usage: gh-create-repo.sh <name> [-d "desc"] [-t topics] [-u url] [--version]
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
INIT_VERSION=false
VERSION_TAG="v0.0.0"

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
    echo "  -u, --url URL         Homepage URL (shown on GitHub page)"
    echo "  -t, --topics TOPICS   Comma-separated topics/tags"
    echo "  --public              Create public repository (default: private)"
    echo "  --internal            Create internal repository (Enterprise only)"
    echo "  --init                Initialize with README"
    echo "  --gitignore LANG      Add .gitignore template (e.g., Python, Node)"
    echo "  --license LICENSE     Add license (e.g., MIT, Apache-2.0)"
    echo "  --version [TAG]       Create initial version tag (default: v0.0.0)"
    echo "  --clone               Clone repository after creation"
    echo "  --dry-run             Show what would be created"
    echo "  --help                Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  # Create private repo with description"
    echo "  gh-create-repo.sh my-project -d 'My awesome project'"
    echo ""
    echo "  # Create public repo with all metadata"
    echo "  gh-create-repo.sh my-project --public \\"
    echo "    -d 'Project description' \\"
    echo "    -u 'https://example.com' \\"
    echo "    -t 'python,cli,devtools' \\"
    echo "    --version"
    echo ""
    echo "  # Create in organization with full setup"
    echo "  gh-create-repo.sh -o myorg my-project --public --init \\"
    echo "    --gitignore Python --license MIT \\"
    echo "    -d 'Description' -t 'python,api' --version --clone"
    echo ""
    echo -e "${BOLD}GitHub Page Fields:${NC}"
    echo "  The following are displayed on the GitHub repository page:"
    echo "  - Description (-d): Short text below repo name"
    echo "  - Homepage URL (-u): Link shown next to description"
    echo "  - Topics (-t): Clickable tags for discoverability"
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
        echo "Run: gh-auth login"
        exit 1
    fi
}

# Create initial version tag
create_version_tag() {
    local repo="$1"
    local tag="$2"
    local clone_dir="$3"

    echo ""
    echo -e "${CYAN}Creating initial version tag: $tag${NC}"

    if [ -n "$clone_dir" ] && [ -d "$clone_dir" ]; then
        # Create tag locally and push
        cd "$clone_dir"
        git tag "$tag"
        git push origin "$tag"
        cd - > /dev/null
        echo -e "${GREEN}Tag $tag created and pushed${NC}"
    else
        # Use gh api to create tag
        # First get the default branch SHA
        local default_branch
        default_branch=$(gh repo view "$repo" --json defaultBranchRef -q '.defaultBranchRef.name')

        local sha
        sha=$(gh api "repos/$repo/git/refs/heads/$default_branch" -q '.object.sha' 2>/dev/null)

        if [ -n "$sha" ]; then
            # Create tag reference
            gh api "repos/$repo/git/refs" \
                -f ref="refs/tags/$tag" \
                -f sha="$sha" > /dev/null 2>&1

            echo -e "${GREEN}Tag $tag created${NC}"
        else
            echo -e "${YELLOW}Warning: Could not create tag (no commits yet?)${NC}"
            echo "  You can create the tag manually after first commit:"
            echo "  git tag $tag && git push origin $tag"
        fi
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
        -u|--url|--homepage)
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
        --version)
            INIT_VERSION=true
            # Check if next arg is a version tag (starts with v)
            if [[ "${2:-}" =~ ^v[0-9] ]]; then
                VERSION_TAG="$2"
                shift
            fi
            shift
            ;;
        --clone)
            CLONE_AFTER=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
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
echo -e "${BOLD}${CYAN}+---------------------------------------------------------------+${NC}"
echo -e "${BOLD}${CYAN}|                  GitHub Repository Creator                    |${NC}"
echo -e "${BOLD}${CYAN}+---------------------------------------------------------------+${NC}"
echo ""

# Determine full repo name
if [ -n "$ORG" ]; then
    FULL_NAME="$ORG/$REPO_NAME"
else
    FULL_NAME="$REPO_NAME"
fi

echo -e "${CYAN}Repository:${NC}  $FULL_NAME"
echo -e "${CYAN}Visibility:${NC}  $VISIBILITY"
[ -n "$DESCRIPTION" ] && echo -e "${CYAN}Description:${NC} $DESCRIPTION"
[ -n "$HOMEPAGE" ] && echo -e "${CYAN}Homepage:${NC}    $HOMEPAGE"
[ -n "$TOPICS" ] && echo -e "${CYAN}Topics:${NC}      $TOPICS"
[ "$INIT_README" = true ] && echo -e "${CYAN}Initialize:${NC}  Yes (with README)"
[ -n "$ADD_GITIGNORE" ] && echo -e "${CYAN}Gitignore:${NC}   $ADD_GITIGNORE"
[ -n "$ADD_LICENSE" ] && echo -e "${CYAN}License:${NC}     $ADD_LICENSE"
[ "$INIT_VERSION" = true ] && echo -e "${CYAN}Version Tag:${NC} $VERSION_TAG"
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
        IFS=',' read -ra TOPIC_ARRAY <<< "$TOPICS"
        for topic in "${TOPIC_ARRAY[@]}"; do
            topic=$(echo "$topic" | xargs)
            [ -n "$topic" ] && echo "  gh repo edit $FULL_NAME --add-topic \"$topic\""
        done
    fi

    if [ "$INIT_VERSION" = true ]; then
        echo "  git tag $VERSION_TAG && git push origin $VERSION_TAG"
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
    echo -e "${GREEN}Repository created${NC}"
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
    TOPICS_ADDED=0
    for topic in "${TOPIC_ARRAY[@]}"; do
        topic=$(echo "$topic" | xargs)  # trim whitespace
        if [ -n "$topic" ]; then
            if gh repo edit "$FULL_NAME" --add-topic "$topic" 2>&1; then
                TOPICS_ADDED=$((TOPICS_ADDED + 1))
            else
                echo -e "${YELLOW}Warning: Could not add topic '$topic'${NC}"
            fi
        fi
    done
    if [ "$TOPICS_ADDED" -gt 0 ]; then
        echo -e "${GREEN}$TOPICS_ADDED topic(s) added${NC}"
    fi
fi

# Clone if requested (do this before version tag if both specified)
CLONE_DIR=""
if [ "$CLONE_AFTER" = true ]; then
    echo ""
    echo -e "${CYAN}Cloning repository...${NC}"
    gh repo clone "$FULL_NAME"
    CLONE_DIR="$REPO_NAME"
    echo -e "${GREEN}Repository cloned to ./$REPO_NAME${NC}"
fi

# Create version tag if requested
if [ "$INIT_VERSION" = true ]; then
    # Need at least one commit for a tag
    if [ "$INIT_README" = true ] || [ -n "$ADD_LICENSE" ] || [ -n "$ADD_GITIGNORE" ]; then
        create_version_tag "$FULL_NAME" "$VERSION_TAG" "$CLONE_DIR"
    else
        echo ""
        echo -e "${YELLOW}Note: Version tag requires at least one commit.${NC}"
        echo "  Use --init, --license, or --gitignore to create initial commit,"
        echo "  or create the tag manually after your first commit:"
        echo "  git tag $VERSION_TAG && git push origin $VERSION_TAG"
    fi
fi

# Get repo URL
REPO_URL=$(gh repo view "$FULL_NAME" --json url -q '.url')

echo ""
echo -e "${GREEN}Repository ready!${NC}"
echo ""
echo -e "${CYAN}URL:${NC} $REPO_URL"

# Show what's configured on GitHub page
echo ""
echo -e "${BOLD}GitHub Page Info:${NC}"
[ -n "$DESCRIPTION" ] && echo -e "  Description: $DESCRIPTION"
[ -n "$HOMEPAGE" ] && echo -e "  Homepage:    $HOMEPAGE"
[ -n "$TOPICS" ] && echo -e "  Topics:      $TOPICS"
[ "$INIT_VERSION" = true ] && echo -e "  Version:     $VERSION_TAG"

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
