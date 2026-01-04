#!/bin/bash
# @name: git-mirror
# @description: Mirror repository between git servers
# @category: git
# @usage: git-mirror.sh <source-url> <target-url>
# =============================================================================
# git-mirror.sh - Mirror Repository Between Servers
# Spiegelt ein Repository zwischen verschiedenen Git-Servern
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
MIRROR_DIR="/tmp/git-mirrors"
FORCE=false
DRY_RUN=false
INCLUDE_WIKI=false
INCLUDE_LFS=false

usage() {
    echo ""
    echo -e "${BOLD}git-mirror.sh${NC} - Mirror repository between Git servers"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  git-mirror.sh <source-url> <target-url> [OPTIONS]"
    echo ""
    echo -e "${BOLD}Arguments:${NC}"
    echo "  source-url            Source repository URL"
    echo "  target-url            Target repository URL"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --dir DIR             Working directory for mirror (default: /tmp/git-mirrors)"
    echo "  --force               Force push (overwrite target)"
    echo "  --wiki                Also mirror wiki repository"
    echo "  --lfs                 Include LFS objects"
    echo "  --branches PATTERN    Only mirror matching branches (glob pattern)"
    echo "  --tags                Only mirror tags (no branches)"
    echo "  -d, --dry-run         Show what would be done"
    echo "  -h, --help            Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  # Mirror GitHub to GitLab"
    echo "  git-mirror.sh https://github.com/org/repo.git https://gitlab.com/org/repo.git"
    echo ""
    echo "  # Mirror with force push"
    echo "  git-mirror.sh git@github.com:org/repo.git git@gitlab.com:org/repo.git --force"
    echo ""
    echo "  # Mirror only main branch"
    echo "  git-mirror.sh source.git target.git --branches 'main'"
    echo ""
    echo "  # Mirror including wiki"
    echo "  git-mirror.sh source.git target.git --wiki"
    echo ""
    echo "  # Mirror with LFS support"
    echo "  git-mirror.sh source.git target.git --lfs"
    echo ""
}

# Extract repo name from URL
get_repo_name() {
    local url="$1"
    basename "$url" .git
}

# Convert repo URL to wiki URL
get_wiki_url() {
    local url="$1"
    # GitHub/GitLab wiki convention: repo.wiki.git
    echo "${url%.git}.wiki.git"
}

# Mirror a single repository
mirror_repo() {
    local source="$1"
    local target="$2"
    local name="$3"
    local work_dir="$MIRROR_DIR/$name"

    echo -e "${CYAN}→${NC} Mirroring: $name"
    echo "  Source: $source"
    echo "  Target: $target"

    if [ "$DRY_RUN" = true ]; then
        echo -e "  ${YELLOW}DRY RUN - Would mirror repository${NC}"
        return 0
    fi

    # Create/update bare mirror clone
    if [ -d "$work_dir" ]; then
        echo "  Updating existing mirror..."
        cd "$work_dir"

        # Fetch all updates from source
        if ! git fetch --all --prune 2>/dev/null; then
            echo -e "  ${RED}✗${NC} Failed to fetch from source"
            return 1
        fi

        # Fetch tags
        git fetch --tags --prune 2>/dev/null || true

    else
        echo "  Creating new mirror clone..."
        mkdir -p "$MIRROR_DIR"

        if ! git clone --mirror "$source" "$work_dir" 2>/dev/null; then
            echo -e "  ${RED}✗${NC} Failed to clone from source"
            return 1
        fi

        cd "$work_dir"
    fi

    # Handle LFS if requested
    if [ "$INCLUDE_LFS" = true ]; then
        if command -v git-lfs &> /dev/null; then
            echo "  Fetching LFS objects..."
            git lfs fetch --all 2>/dev/null || true
        else
            echo -e "  ${YELLOW}!${NC} git-lfs not installed, skipping LFS"
        fi
    fi

    # Set target remote
    if git remote get-url target &>/dev/null; then
        git remote set-url target "$target"
    else
        git remote add target "$target"
    fi

    # Push to target
    echo "  Pushing to target..."

    local push_args=("--mirror")
    if [ "$FORCE" = true ]; then
        push_args+=("--force")
    fi

    # Filter branches if pattern specified
    if [ -n "$BRANCH_PATTERN" ]; then
        # For specific branches, we can't use --mirror
        # Instead push matching refs
        echo "  Filtering branches: $BRANCH_PATTERN"

        # Get matching branches
        local branches
        branches=$(git branch -a --list "*$BRANCH_PATTERN*" 2>/dev/null | sed 's/^[* ]*//' | grep -v '^remotes/' || true)

        if [ -z "$branches" ]; then
            echo -e "  ${YELLOW}!${NC} No branches matching pattern"
        else
            for branch in $branches; do
                local push_cmd=("git" "push" "target" "$branch:$branch")
                [ "$FORCE" = true ] && push_cmd+=("--force")

                if "${push_cmd[@]}" 2>/dev/null; then
                    echo -e "    ${GREEN}✓${NC} $branch"
                else
                    echo -e "    ${RED}✗${NC} $branch"
                fi
            done
        fi

        # Always push tags
        git push target --tags 2>/dev/null || true

    elif [ "$TAGS_ONLY" = true ]; then
        # Only push tags
        if git push target --tags ${FORCE:+--force} 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Tags pushed"
        else
            echo -e "  ${RED}✗${NC} Failed to push tags"
            return 1
        fi
    else
        # Full mirror push
        if git push target "${push_args[@]}" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Mirror complete"
        else
            echo -e "  ${RED}✗${NC} Failed to push to target"
            return 1
        fi
    fi

    # Push LFS objects
    if [ "$INCLUDE_LFS" = true ]; then
        if command -v git-lfs &> /dev/null; then
            echo "  Pushing LFS objects..."
            git lfs push target --all 2>/dev/null || true
        fi
    fi

    return 0
}

# Parse arguments
SOURCE_URL=""
TARGET_URL=""
BRANCH_PATTERN=""
TAGS_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)
            MIRROR_DIR="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --wiki)
            INCLUDE_WIKI=true
            shift
            ;;
        --lfs)
            INCLUDE_LFS=true
            shift
            ;;
        --branches)
            BRANCH_PATTERN="$2"
            shift 2
            ;;
        --tags)
            TAGS_ONLY=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
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
            if [ -z "$SOURCE_URL" ]; then
                SOURCE_URL="$1"
            elif [ -z "$TARGET_URL" ]; then
                TARGET_URL="$1"
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
if [ -z "$SOURCE_URL" ] || [ -z "$TARGET_URL" ]; then
    echo -e "${RED}[ERROR] Both source and target URLs required${NC}"
    usage
    exit 1
fi

# Main
echo ""
echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                    Git Repository Mirror                      ║${NC}"
echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

REPO_NAME=$(get_repo_name "$SOURCE_URL")

echo -e "${CYAN}Repository:${NC} $REPO_NAME"
echo -e "${CYAN}Source:${NC} $SOURCE_URL"
echo -e "${CYAN}Target:${NC} $TARGET_URL"
echo -e "${CYAN}Work Dir:${NC} $MIRROR_DIR"
[ "$FORCE" = true ] && echo -e "${YELLOW}Force push enabled${NC}"
[ "$INCLUDE_LFS" = true ] && echo -e "${CYAN}LFS:${NC} enabled"
[ "$INCLUDE_WIKI" = true ] && echo -e "${CYAN}Wiki:${NC} enabled"
[ -n "$BRANCH_PATTERN" ] && echo -e "${CYAN}Branch filter:${NC} $BRANCH_PATTERN"
[ "$TAGS_ONLY" = true ] && echo -e "${CYAN}Mode:${NC} tags only"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN - No changes will be made${NC}"
    echo ""
fi

# Mirror main repository
if mirror_repo "$SOURCE_URL" "$TARGET_URL" "$REPO_NAME"; then
    MAIN_SUCCESS=true
else
    MAIN_SUCCESS=false
fi

# Mirror wiki if requested
WIKI_SUCCESS=true
if [ "$INCLUDE_WIKI" = true ]; then
    echo ""
    WIKI_SOURCE=$(get_wiki_url "$SOURCE_URL")
    WIKI_TARGET=$(get_wiki_url "$TARGET_URL")

    if mirror_repo "$WIKI_SOURCE" "$WIKI_TARGET" "${REPO_NAME}.wiki"; then
        WIKI_SUCCESS=true
    else
        WIKI_SUCCESS=false
        echo -e "  ${YELLOW}!${NC} Wiki mirror failed (wiki may not exist)"
    fi
fi

# Summary
echo ""
if [ "$MAIN_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ Repository mirrored successfully${NC}"
else
    echo -e "${RED}✗ Repository mirror failed${NC}"
fi

if [ "$INCLUDE_WIKI" = true ]; then
    if [ "$WIKI_SUCCESS" = true ]; then
        echo -e "${GREEN}✓ Wiki mirrored${NC}"
    else
        echo -e "${YELLOW}○ Wiki not mirrored${NC}"
    fi
fi

echo ""
echo -e "Mirror cached in: ${CYAN}$MIRROR_DIR/$REPO_NAME${NC}"
echo ""

[ "$MAIN_SUCCESS" = false ] && exit 1
exit 0
