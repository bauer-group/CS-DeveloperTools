#!/bin/bash
# @name: git-history-clean
# @description: Remove large files from git history
# @category: git
# @usage: git-history-clean.sh [--size 10M] [--dry-run]
# =============================================================================
# git-history-clean.sh - Remove Large Files from Git History
# Entfernt große Dateien aus der Git-Historie mit git-filter-repo
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
MAX_SIZE="50M"
DRY_RUN=false
AGGRESSIVE_GC=false

usage() {
    echo ""
    echo -e "${BOLD}git-history-clean.sh${NC} - Remove large files from Git history"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  git-history-clean.sh [OPTIONS]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -s, --size SIZE       Max file size to keep (default: 50M)"
    echo "                        Examples: 10M, 100M, 1G"
    echo "  -d, --dry-run         Show what would be removed without changing"
    echo "  -g, --aggressive-gc   Run aggressive garbage collection after"
    echo "  -a, --analyze         Only analyze, show large files in history"
    echo "  -h, --help            Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  git-history-clean.sh --analyze           # Show large files"
    echo "  git-history-clean.sh --dry-run           # Preview cleanup"
    echo "  git-history-clean.sh -s 100M             # Remove files > 100MB"
    echo "  git-history-clean.sh -s 50M -g           # Clean + aggressive GC"
    echo ""
    echo -e "${YELLOW}WARNING: This rewrites git history!${NC}"
    echo "After running, you'll need to force-push: git push --force"
    echo ""
}

# Check dependencies
check_dependencies() {
    if ! command -v git-filter-repo &> /dev/null; then
        echo -e "${RED}[ERROR] git-filter-repo not found${NC}"
        echo "Install with: pip install git-filter-repo"
        exit 1
    fi
}

# Check if in git repo
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}[ERROR] Not a git repository${NC}"
        exit 1
    fi
}

# Analyze large files in history
analyze_large_files() {
    echo ""
    echo -e "${BOLD}${CYAN}═══ Analyzing Large Files in History ═══${NC}"
    echo ""

    # Find large blobs in history
    echo -e "${YELLOW}Large files (sorted by size):${NC}"
    echo ""

    git rev-list --objects --all | \
        git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
        sed -n 's/^blob //p' | \
        sort -rnk2 | \
        head -20 | \
        while read hash size path; do
            size_mb=$(echo "scale=2; $size / 1048576" | bc)
            if (( $(echo "$size_mb >= 1" | bc -l) )); then
                printf "  ${CYAN}%8.2f MB${NC}  %s\n" "$size_mb" "$path"
            fi
        done

    echo ""

    # Show current repo size
    REPO_SIZE=$(du -sh .git 2>/dev/null | cut -f1)
    echo -e "${CYAN}Current .git size:${NC} $REPO_SIZE"
    echo ""
}

# Show packfile sizes
show_packfile_size() {
    PACK_DIR=".git/objects/pack"
    if [ -d "$PACK_DIR" ]; then
        echo -e "${CYAN}Packfile sizes:${NC}"
        for file in "$PACK_DIR"/*.pack; do
            if [ -f "$file" ]; then
                SIZE=$(du -h "$file" | cut -f1)
                echo "  $(basename "$file"): $SIZE"
            fi
        done
    fi
}

# Clean repository
clean_repo() {
    local size="$1"

    echo ""
    echo -e "${BOLD}${CYAN}═══ Cleaning Git History ═══${NC}"
    echo ""
    echo -e "${YELLOW}Removing files larger than: $size${NC}"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}DRY RUN - No changes will be made${NC}"
        echo ""
        echo "Would run: git filter-repo --strip-blobs-bigger-than $size --force"
        return
    fi

    # Confirmation
    echo -e "${RED}WARNING: This will rewrite git history!${NC}"
    read -p "Continue? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[yY]$ ]]; then
        echo "Aborted."
        exit 0
    fi

    echo ""
    echo -e "${CYAN}Running git-filter-repo...${NC}"
    git filter-repo --strip-blobs-bigger-than "$size" --force

    echo ""
    echo -e "${GREEN}✓ History cleaned${NC}"

    # Repack
    echo ""
    echo -e "${CYAN}Repacking repository...${NC}"
    git repack -a -d -f

    if [ "$AGGRESSIVE_GC" = true ]; then
        echo ""
        echo -e "${CYAN}Running aggressive garbage collection...${NC}"
        git gc --aggressive --prune=now
    fi

    echo ""
    show_packfile_size

    echo ""
    echo -e "${GREEN}✓ Cleanup complete${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Verify the repository: git log --oneline -10"
    echo "  2. Force push to remote: git push --force --all"
    echo "  3. Force push tags: git push --force --tags"
    echo ""
}

# Parse arguments
ANALYZE_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--size)
            MAX_SIZE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -g|--aggressive-gc)
            AGGRESSIVE_GC=true
            shift
            ;;
        -a|--analyze)
            ANALYZE_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Main
check_git_repo
check_dependencies

if [ "$ANALYZE_ONLY" = true ]; then
    analyze_large_files
else
    analyze_large_files
    clean_repo "$MAX_SIZE"
fi
