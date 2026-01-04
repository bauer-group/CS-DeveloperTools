#!/bin/bash
# @name: git-stats
# @description: Show repository statistics
# @category: git
# @usage: git-stats.sh
# =============================================================================
# git-stats.sh - Repository Statistics
# Zeigt umfassende Statistiken zum Git-Repository
# =============================================================================

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Prüfen ob wir in einem Git-Repository sind
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}"
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║                    Git Repository Statistics                   ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Repository Info
echo -e "${CYAN}📁 Repository:${NC} $REPO_NAME"
echo -e "${CYAN}📍 Path:${NC}       $REPO_ROOT"

# Remote Info
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "No remote")
echo -e "${CYAN}🔗 Remote:${NC}     $REMOTE_URL"

# Branch Info
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
echo -e "${CYAN}🌿 Branch:${NC}     $CURRENT_BRANCH (default: $DEFAULT_BRANCH)"
echo ""

# Commit Statistics
echo -e "${BOLD}${GREEN}═══ Commit Statistics ═══${NC}"
TOTAL_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")
echo -e "Total commits:          ${YELLOW}$TOTAL_COMMITS${NC}"

FIRST_COMMIT=$(git log --reverse --format="%ci" 2>/dev/null | head -1 | cut -d' ' -f1)
LAST_COMMIT=$(git log -1 --format="%ci" 2>/dev/null | cut -d' ' -f1)
echo -e "First commit:           $FIRST_COMMIT"
echo -e "Last commit:            $LAST_COMMIT"

# Commits in last periods
COMMITS_TODAY=$(git log --since="midnight" --oneline 2>/dev/null | wc -l)
COMMITS_WEEK=$(git log --since="1 week ago" --oneline 2>/dev/null | wc -l)
COMMITS_MONTH=$(git log --since="1 month ago" --oneline 2>/dev/null | wc -l)
echo -e "Commits today:          ${YELLOW}$COMMITS_TODAY${NC}"
echo -e "Commits this week:      ${YELLOW}$COMMITS_WEEK${NC}"
echo -e "Commits this month:     ${YELLOW}$COMMITS_MONTH${NC}"
echo ""

# Branch Statistics
echo -e "${BOLD}${GREEN}═══ Branch Statistics ═══${NC}"
LOCAL_BRANCHES=$(git branch | wc -l)
REMOTE_BRANCHES=$(git branch -r 2>/dev/null | grep -v HEAD | wc -l)
echo -e "Local branches:         ${YELLOW}$LOCAL_BRANCHES${NC}"
echo -e "Remote branches:        ${YELLOW}$REMOTE_BRANCHES${NC}"

# Stale branches (no commits in 30 days)
STALE_BRANCHES=$(git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:relative)' refs/heads/ 2>/dev/null | \
    grep -E "(month|year)" | wc -l)
if [ "$STALE_BRANCHES" -gt 0 ]; then
    echo -e "Stale branches (>30d):  ${RED}$STALE_BRANCHES${NC}"
fi
echo ""

# Tag Statistics
echo -e "${BOLD}${GREEN}═══ Tag Statistics ═══${NC}"
TOTAL_TAGS=$(git tag | wc -l)
echo -e "Total tags:             ${YELLOW}$TOTAL_TAGS${NC}"

if [ "$TOTAL_TAGS" -gt 0 ]; then
    LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
    echo -e "Latest tag:             ${YELLOW}$LATEST_TAG${NC}"
fi
echo ""

# Contributor Statistics
echo -e "${BOLD}${GREEN}═══ Top Contributors ═══${NC}"
git shortlog -sn --all 2>/dev/null | head -5 | while read -r count name; do
    printf "  ${MAGENTA}%-30s${NC} %s commits\n" "$name" "$count"
done
echo ""

# File Statistics
echo -e "${BOLD}${GREEN}═══ File Statistics ═══${NC}"
TOTAL_FILES=$(git ls-files 2>/dev/null | wc -l)
echo -e "Tracked files:          ${YELLOW}$TOTAL_FILES${NC}"

# Lines of code (nur wenn cloc oder wc verfügbar)
if command -v wc &> /dev/null; then
    TOTAL_LINES=$(git ls-files 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
    echo -e "Total lines:            ${YELLOW}$TOTAL_LINES${NC}"
fi

# File types
echo -e "\nTop file types:"
git ls-files 2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -5 | while read -r count ext; do
    printf "  ${CYAN}%-15s${NC} %s files\n" ".$ext" "$count"
done
echo ""

# Working Tree Status
echo -e "${BOLD}${GREEN}═══ Working Tree Status ═══${NC}"
MODIFIED=$(git status --porcelain 2>/dev/null | grep "^ M" | wc -l)
ADDED=$(git status --porcelain 2>/dev/null | grep "^A" | wc -l)
DELETED=$(git status --porcelain 2>/dev/null | grep "^.D" | wc -l)
UNTRACKED=$(git status --porcelain 2>/dev/null | grep "^??" | wc -l)
STAGED=$(git status --porcelain 2>/dev/null | grep "^[MADRC]" | wc -l)

echo -e "Modified files:         ${YELLOW}$MODIFIED${NC}"
echo -e "Staged files:           ${GREEN}$STAGED${NC}"
echo -e "Deleted files:          ${RED}$DELETED${NC}"
echo -e "Untracked files:        ${CYAN}$UNTRACKED${NC}"

# Stash Status
STASH_COUNT=$(git stash list 2>/dev/null | wc -l)
if [ "$STASH_COUNT" -gt 0 ]; then
    echo -e "Stashed changes:        ${MAGENTA}$STASH_COUNT${NC}"
fi
echo ""

# Size Information
echo -e "${BOLD}${GREEN}═══ Repository Size ═══${NC}"
GIT_SIZE=$(du -sh "$REPO_ROOT/.git" 2>/dev/null | cut -f1)
REPO_SIZE=$(du -sh "$REPO_ROOT" 2>/dev/null | cut -f1)
echo -e ".git directory:         ${YELLOW}$GIT_SIZE${NC}"
echo -e "Total repository:       ${YELLOW}$REPO_SIZE${NC}"
echo ""
