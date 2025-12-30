#!/bin/bash
# =============================================================================
# git-branch-rename.sh - Rename Git Branches (Local + Remote)
# Benennt Branches um und aktualisiert Remote + Default Branch
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
OLD_BRANCH=""
NEW_BRANCH=""
UPDATE_DEFAULT=false
DRY_RUN=false

usage() {
    echo ""
    echo -e "${BOLD}git-branch-rename.sh${NC} - Rename branches locally and on remote"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  git-branch-rename.sh <old-name> <new-name> [OPTIONS]"
    echo "  git-branch-rename.sh --master-to-main [OPTIONS]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --master-to-main      Quick rename from 'master' to 'main'"
    echo "  -u, --update-default  Update GitHub default branch (requires gh CLI)"
    echo "  -d, --dry-run         Show what would be done without changes"
    echo "  -h, --help            Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  git-branch-rename.sh master main -u       # Rename + update default"
    echo "  git-branch-rename.sh --master-to-main -u  # Quick master→main"
    echo "  git-branch-rename.sh develop development  # Rename any branch"
    echo ""
}

# Run command with optional dry-run
run_cmd() {
    local cmd="$1"
    echo -e "${CYAN}→${NC} $cmd"

    if [ "$DRY_RUN" = true ]; then
        return 0
    fi

    eval "$cmd"
}

# Check if in git repo
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}[ERROR] Not a git repository${NC}"
        exit 1
    fi
}

# Check if branch exists
branch_exists() {
    local branch="$1"
    git show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null
}

# Check if remote branch exists
remote_branch_exists() {
    local branch="$1"
    git ls-remote --exit-code --heads origin "$branch" &>/dev/null
}

# Get origin URL
get_origin_url() {
    git remote get-url origin 2>/dev/null
}

# Extract owner/repo from GitHub URL
extract_owner_repo() {
    local url="$1"
    echo "$url" | sed -E 's#.*github\.com[:/]([^/]+)/([^/.]+)(\.git)?$#\1/\2#'
}

# Update GitHub default branch
update_github_default() {
    local owner_repo="$1"
    local new_branch="$2"

    if ! command -v gh &> /dev/null; then
        echo -e "${YELLOW}Warning: gh CLI not found, skipping default branch update${NC}"
        return
    fi

    echo ""
    echo -e "${CYAN}Updating GitHub default branch...${NC}"

    if [ "$DRY_RUN" = true ]; then
        echo "Would run: gh api -X PATCH repos/$owner_repo -f default_branch=$new_branch"
        return
    fi

    if gh api -X PATCH "repos/$owner_repo" -f "default_branch=$new_branch" &>/dev/null; then
        echo -e "${GREEN}✓ Default branch updated to '$new_branch'${NC}"
    else
        echo -e "${YELLOW}Warning: Could not update default branch${NC}"
    fi
}

# Main rename function
rename_branch() {
    local old_branch="$1"
    local new_branch="$2"

    echo ""
    echo -e "${BOLD}${CYAN}═══ Git Branch Rename ═══${NC}"
    echo ""
    echo -e "Old branch: ${YELLOW}$old_branch${NC}"
    echo -e "New branch: ${GREEN}$new_branch${NC}"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
        echo ""
    fi

    # Check if old branch exists
    if ! branch_exists "$old_branch"; then
        if branch_exists "$new_branch"; then
            echo -e "${YELLOW}Branch '$new_branch' already exists locally.${NC}"
            echo "No local rename needed."
        else
            echo -e "${RED}[ERROR] Neither '$old_branch' nor '$new_branch' exists locally${NC}"
            exit 1
        fi
    else
        # Step 1: Checkout old branch
        echo -e "${BOLD}Step 1: Checkout '$old_branch'${NC}"
        run_cmd "git checkout $old_branch"

        # Step 2: Rename locally
        echo ""
        echo -e "${BOLD}Step 2: Rename local branch${NC}"
        run_cmd "git branch -m $old_branch $new_branch"
    fi

    # Step 3: Push new branch
    echo ""
    echo -e "${BOLD}Step 3: Push '$new_branch' to remote${NC}"
    run_cmd "git push -u origin $new_branch"

    # Step 4: Update default branch on GitHub
    if [ "$UPDATE_DEFAULT" = true ]; then
        local url
        url=$(get_origin_url)
        if [[ "$url" == *"github.com"* ]]; then
            local owner_repo
            owner_repo=$(extract_owner_repo "$url")
            update_github_default "$owner_repo" "$new_branch"
        fi
    fi

    # Step 5: Delete old remote branch
    echo ""
    echo -e "${BOLD}Step 5: Delete old remote branch${NC}"
    if remote_branch_exists "$old_branch"; then
        run_cmd "git push origin --delete $old_branch" || \
            echo -e "${YELLOW}Warning: Could not delete remote '$old_branch' (may not exist)${NC}"
    else
        echo "Remote branch '$old_branch' not found (already deleted?)"
    fi

    echo ""
    echo -e "${GREEN}═══ Branch Rename Complete ═══${NC}"
    echo ""
    echo -e "Branch '${YELLOW}$old_branch${NC}' renamed to '${GREEN}$new_branch${NC}'"

    if [ "$DRY_RUN" = false ]; then
        echo ""
        echo -e "${CYAN}Current branches:${NC}"
        git branch -vv
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --master-to-main)
            OLD_BRANCH="master"
            NEW_BRANCH="main"
            shift
            ;;
        -u|--update-default)
            UPDATE_DEFAULT=true
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
            if [ -z "$OLD_BRANCH" ]; then
                OLD_BRANCH="$1"
            elif [ -z "$NEW_BRANCH" ]; then
                NEW_BRANCH="$1"
            else
                echo -e "${RED}Too many arguments${NC}"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate
if [ -z "$OLD_BRANCH" ] || [ -z "$NEW_BRANCH" ]; then
    echo -e "${RED}[ERROR] Both old and new branch names are required${NC}"
    usage
    exit 1
fi

if [ "$OLD_BRANCH" = "$NEW_BRANCH" ]; then
    echo -e "${RED}[ERROR] Old and new branch names are the same${NC}"
    exit 1
fi

# Run
check_git_repo
rename_branch "$OLD_BRANCH" "$NEW_BRANCH"
