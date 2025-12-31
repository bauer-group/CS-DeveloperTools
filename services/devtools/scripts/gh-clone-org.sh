#!/bin/bash
# =============================================================================
# gh-clone-org.sh - Clone All Repositories from Organization
# Klont alle Repositories einer Organisation (mit Filtern)
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
OUTPUT_DIR="."
CLONE_METHOD="https"
INCLUDE_ARCHIVED=false
INCLUDE_FORKS=false
SHALLOW=false
PARALLEL=4
DRY_RUN=false

usage() {
    echo ""
    echo -e "${BOLD}gh-clone-org.sh${NC} - Clone all repositories from organization"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  gh-clone-org.sh <org> [OPTIONS]"
    echo ""
    echo -e "${BOLD}Arguments:${NC}"
    echo "  org                     Organization name"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -o, --output DIR        Output directory (default: current)"
    echo "  -t, --topic TOPIC       Only repos with this topic"
    echo "  -p, --pattern PATTERN   Only repos matching pattern"
    echo "  --ssh                   Use SSH instead of HTTPS"
    echo "  --archived              Include archived repositories"
    echo "  --forks                 Include forked repositories"
    echo "  --shallow               Shallow clone (--depth 1)"
    echo "  --parallel N            Parallel clones (default: 4)"
    echo "  --pull                  Pull instead of clone (update existing)"
    echo "  -d, --dry-run           Show what would be cloned"
    echo "  -h, --help              Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  # Clone all repos from org"
    echo "  gh-clone-org.sh myorg"
    echo ""
    echo "  # Clone to specific directory"
    echo "  gh-clone-org.sh myorg -o ~/backup/myorg"
    echo ""
    echo "  # Clone only repos with topic"
    echo "  gh-clone-org.sh myorg -t python"
    echo ""
    echo "  # Clone repos matching pattern"
    echo "  gh-clone-org.sh myorg -p 'api-*'"
    echo ""
    echo "  # Shallow clone using SSH"
    echo "  gh-clone-org.sh myorg --ssh --shallow"
    echo ""
    echo "  # Update existing clones"
    echo "  gh-clone-org.sh myorg --pull"
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

# Clone or pull a repository
clone_repo() {
    local repo_name="$1"
    local clone_url="$2"
    local target_dir="$3"
    local do_pull="$4"

    if [ -d "$target_dir/.git" ]; then
        if [ "$do_pull" = true ]; then
            echo -e "  ${CYAN}→${NC} Pulling $repo_name..."
            if git -C "$target_dir" pull --ff-only 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Updated $repo_name"
            else
                echo -e "  ${YELLOW}!${NC} $repo_name (merge needed)"
            fi
        else
            echo -e "  ${YELLOW}○${NC} Skipped $repo_name (exists)"
        fi
        return 0
    fi

    echo -e "  ${CYAN}→${NC} Cloning $repo_name..."

    local clone_args=()
    if [ "$SHALLOW" = true ]; then
        clone_args+=("--depth" "1")
    fi

    if git clone "${clone_args[@]}" "$clone_url" "$target_dir" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Cloned $repo_name"
        return 0
    else
        echo -e "  ${RED}✗${NC} Failed $repo_name"
        return 1
    fi
}

# Parse arguments
ORG=""
TOPIC=""
PATTERN=""
DO_PULL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -t|--topic)
            TOPIC="$2"
            shift 2
            ;;
        -p|--pattern)
            PATTERN="$2"
            shift 2
            ;;
        --ssh)
            CLONE_METHOD="ssh"
            shift
            ;;
        --archived)
            INCLUDE_ARCHIVED=true
            shift
            ;;
        --forks)
            INCLUDE_FORKS=true
            shift
            ;;
        --shallow)
            SHALLOW=true
            shift
            ;;
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --pull)
            DO_PULL=true
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
            if [ -z "$ORG" ]; then
                ORG="$1"
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
if [ -z "$ORG" ]; then
    echo -e "${RED}[ERROR] Organization name required${NC}"
    usage
    exit 1
fi

# Main
check_dependencies

echo ""
echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                  GitHub Organization Cloner                   ║${NC}"
echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Organization:${NC} $ORG"
echo -e "${CYAN}Output:${NC} $OUTPUT_DIR"
echo -e "${CYAN}Method:${NC} $CLONE_METHOD"
[ -n "$TOPIC" ] && echo -e "${CYAN}Topic:${NC} $TOPIC"
[ -n "$PATTERN" ] && echo -e "${CYAN}Pattern:${NC} $PATTERN"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Get repositories
echo -e "${CYAN}Fetching repositories...${NC}"

QUERY="owner:$ORG"
[ "$INCLUDE_ARCHIVED" = false ] && QUERY="$QUERY archived:false"
[ "$INCLUDE_FORKS" = false ] && QUERY="$QUERY fork:false"
[ -n "$TOPIC" ] && QUERY="$QUERY topic:$TOPIC"

REPOS=$(gh repo list "$ORG" --json name,sshUrl,url,isArchived,isFork --limit 1000 -q '.[] | @base64')

# Count and filter
TOTAL=0
FILTERED=0

declare -a REPO_LIST

while IFS= read -r repo_b64; do
    [ -z "$repo_b64" ] && continue

    repo_json=$(echo "$repo_b64" | base64 -d)
    name=$(echo "$repo_json" | jq -r '.name')
    ssh_url=$(echo "$repo_json" | jq -r '.sshUrl')
    https_url=$(echo "$repo_json" | jq -r '.url')
    is_archived=$(echo "$repo_json" | jq -r '.isArchived')
    is_fork=$(echo "$repo_json" | jq -r '.isFork')

    TOTAL=$((TOTAL + 1))

    # Filter archived
    if [ "$INCLUDE_ARCHIVED" = false ] && [ "$is_archived" = "true" ]; then
        continue
    fi

    # Filter forks
    if [ "$INCLUDE_FORKS" = false ] && [ "$is_fork" = "true" ]; then
        continue
    fi

    # Filter pattern
    if [ -n "$PATTERN" ]; then
        if [[ ! "$name" == $PATTERN ]]; then
            continue
        fi
    fi

    # Select clone URL
    if [ "$CLONE_METHOD" = "ssh" ]; then
        clone_url="$ssh_url"
    else
        clone_url="${https_url}.git"
    fi

    REPO_LIST+=("$name|$clone_url")
    FILTERED=$((FILTERED + 1))

done <<< "$REPOS"

echo -e "Found ${YELLOW}$FILTERED${NC} repositories (of $TOTAL total)"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN - No changes will be made${NC}"
    echo ""
    echo "Would clone:"
    for entry in "${REPO_LIST[@]}"; do
        name="${entry%%|*}"
        echo "  - $name"
    done
    echo ""
    exit 0
fi

# Clone repositories
echo -e "${BOLD}Cloning repositories...${NC}"
echo ""

SUCCESS=0
FAILED=0
SKIPPED=0

for entry in "${REPO_LIST[@]}"; do
    name="${entry%%|*}"
    clone_url="${entry#*|}"
    target="$OUTPUT_DIR/$name"

    if clone_repo "$name" "$clone_url" "$target" "$DO_PULL"; then
        if [ -d "$target/.git" ]; then
            SUCCESS=$((SUCCESS + 1))
        else
            SKIPPED=$((SKIPPED + 1))
        fi
    else
        FAILED=$((FAILED + 1))
    fi
done

# Summary
echo ""
echo -e "${GREEN}✓ $SUCCESS cloned/updated${NC}"
[ $SKIPPED -gt 0 ] && echo -e "${YELLOW}○ $SKIPPED skipped${NC}"
[ $FAILED -gt 0 ] && echo -e "${RED}✗ $FAILED failed${NC}"
echo ""
echo -e "Repositories saved to: ${CYAN}$OUTPUT_DIR${NC}"
echo ""
