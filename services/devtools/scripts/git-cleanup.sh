#!/bin/bash
# @name: git-cleanup
# @description: Clean up branches, cache and optimize repository
# @category: git
# @usage: git-cleanup.sh [--dry-run] [--all]
# =============================================================================
# git-cleanup.sh - Repository Cleanup Tool
# Bereinigt Branches, Cache und optimiert das Repository
# =============================================================================

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Default values
DRY_RUN=false
FORCE=false
DAYS=30

usage() {
    echo "Usage: git-cleanup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --dry-run       Show what would be deleted without actually deleting"
    echo "  -f, --force         Skip confirmation prompts"
    echo "  -D, --days DAYS     Age threshold for stale branches (default: 30)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Operations:"
    echo "  1. Remove merged local branches"
    echo "  2. Prune remote tracking branches"
    echo "  3. Remove stale branches (no commits in N days)"
    echo "  4. Clean up Git garbage collection"
    echo "  5. Remove untracked files (optional)"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -D|--days)
            DAYS="$2"
            shift 2
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

# Prüfen ob wir in einem Git-Repository sind
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}"
    exit 1
fi

echo ""
echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                    Git Repository Cleanup                      ║${NC}"
echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Get default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

# 1. Merged Branches
echo -e "${BOLD}${GREEN}═══ Step 1: Merged Local Branches ═══${NC}"
MERGED_BRANCHES=$(git branch --merged "$DEFAULT_BRANCH" 2>/dev/null | grep -v "^\*" | grep -v "$DEFAULT_BRANCH" | grep -v "main" | grep -v "master" | grep -v "develop" | tr -d ' ')

if [ -n "$MERGED_BRANCHES" ]; then
    echo -e "Found merged branches that can be deleted:"
    echo "$MERGED_BRANCHES" | while read -r branch; do
        echo -e "  ${RED}✗${NC} $branch"
    done

    if [ "$DRY_RUN" = false ]; then
        if [ "$FORCE" = true ]; then
            CONFIRM="y"
        else
            echo ""
            read -p "Delete these branches? (y/N) " CONFIRM
        fi

        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            echo "$MERGED_BRANCHES" | xargs -r git branch -d 2>/dev/null || true
            echo -e "${GREEN}✓ Merged branches deleted${NC}"
        else
            echo -e "${YELLOW}Skipped${NC}"
        fi
    fi
else
    echo -e "${GREEN}✓ No merged branches to delete${NC}"
fi
echo ""

# 2. Remote Tracking Branches
echo -e "${BOLD}${GREEN}═══ Step 2: Prune Remote Tracking Branches ═══${NC}"
STALE_REMOTES=$(git remote prune origin --dry-run 2>/dev/null | grep "\[would prune\]" | wc -l)

if [ "$STALE_REMOTES" -gt 0 ]; then
    echo -e "Found ${YELLOW}$STALE_REMOTES${NC} stale remote tracking references"
    git remote prune origin --dry-run 2>/dev/null | grep "\[would prune\]" | sed 's/.*\[would prune\]/  ✗/'

    if [ "$DRY_RUN" = false ]; then
        git remote prune origin
        echo -e "${GREEN}✓ Remote tracking branches pruned${NC}"
    fi
else
    echo -e "${GREEN}✓ No stale remote tracking branches${NC}"
fi
echo ""

# 3. Stale Branches (keine Commits seit N Tagen)
echo -e "${BOLD}${GREEN}═══ Step 3: Stale Branches (No commits in $DAYS days) ═══${NC}"
CUTOFF_DATE=$(date -d "$DAYS days ago" +%s 2>/dev/null || date -v-${DAYS}d +%s 2>/dev/null || echo "0")

STALE_BRANCHES=""
while IFS= read -r line; do
    BRANCH=$(echo "$line" | awk '{print $1}')
    # Skip protected branches
    if [[ "$BRANCH" == "main" || "$BRANCH" == "master" || "$BRANCH" == "develop" || "$BRANCH" == "$CURRENT_BRANCH" ]]; then
        continue
    fi

    LAST_COMMIT_DATE=$(git log -1 --format="%ct" "$BRANCH" 2>/dev/null || echo "0")
    if [ "$LAST_COMMIT_DATE" -lt "$CUTOFF_DATE" ] 2>/dev/null; then
        STALE_BRANCHES="$STALE_BRANCHES$BRANCH\n"
    fi
done < <(git branch --format='%(refname:short)')

if [ -n "$STALE_BRANCHES" ]; then
    echo -e "Found stale branches (no commits in $DAYS days):"
    echo -e "$STALE_BRANCHES" | while read -r branch; do
        if [ -n "$branch" ]; then
            LAST_DATE=$(git log -1 --format="%cr" "$branch" 2>/dev/null || echo "unknown")
            echo -e "  ${RED}✗${NC} $branch (last commit: $LAST_DATE)"
        fi
    done

    if [ "$DRY_RUN" = false ] && [ "$FORCE" = false ]; then
        echo ""
        read -p "Delete these stale branches? (y/N) " CONFIRM
        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            echo -e "$STALE_BRANCHES" | while read -r branch; do
                if [ -n "$branch" ]; then
                    git branch -D "$branch" 2>/dev/null || true
                fi
            done
            echo -e "${GREEN}✓ Stale branches deleted${NC}"
        else
            echo -e "${YELLOW}Skipped${NC}"
        fi
    fi
else
    echo -e "${GREEN}✓ No stale branches found${NC}"
fi
echo ""

# 4. Git Garbage Collection
echo -e "${BOLD}${GREEN}═══ Step 4: Git Garbage Collection ═══${NC}"
if [ "$DRY_RUN" = false ]; then
    echo -e "Running git gc --prune=now..."
    git gc --prune=now --quiet
    echo -e "${GREEN}✓ Garbage collection completed${NC}"
else
    echo -e "${YELLOW}Would run: git gc --prune=now${NC}"
fi
echo ""

# 5. Repository Size
echo -e "${BOLD}${GREEN}═══ Repository Size ═══${NC}"
GIT_SIZE=$(du -sh .git 2>/dev/null | cut -f1)
echo -e ".git directory size: ${YELLOW}$GIT_SIZE${NC}"
echo ""

echo -e "${GREEN}✓ Cleanup completed!${NC}"
echo ""
