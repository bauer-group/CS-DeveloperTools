#!/bin/bash
# @name: help-devtools
# @description: Show available DevTools commands
# @category: system
# @usage: help-devtools [--category <cat>] [--json]
# =============================================================================
# help-devtools.sh - DevTools Help System
# Scans scripts and displays available tools from metadata headers
# =============================================================================

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPTS_DIR="/opt/devtools/scripts"
FILTER_CATEGORY=""
OUTPUT_JSON=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --category|-c)
            FILTER_CATEGORY="$2"
            shift 2
            ;;
        --json)
            OUTPUT_JSON=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Function to extract metadata from a script
extract_metadata() {
    local file="$1"
    local name="" description="" category="" usage=""

    # Read first 10 lines and extract @tags
    while IFS= read -r line; do
        if [[ "$line" =~ ^#[[:space:]]*@name:[[:space:]]*(.+)$ ]]; then
            name="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^#[[:space:]]*@description:[[:space:]]*(.+)$ ]]; then
            description="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^#[[:space:]]*@category:[[:space:]]*(.+)$ ]]; then
            category="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^#[[:space:]]*@usage:[[:space:]]*(.+)$ ]]; then
            usage="${BASH_REMATCH[1]}"
        fi
    done < <(head -10 "$file")

    # Return if no metadata found
    [[ -z "$name" ]] && return 1

    # Filter by category if specified
    if [[ -n "$FILTER_CATEGORY" && "$category" != "$FILTER_CATEGORY" ]]; then
        return 1
    fi

    echo "$name|$description|$category|$usage"
}

# Collect all tools
declare -A TOOLS_BY_CATEGORY

for script in "$SCRIPTS_DIR"/*.sh "$SCRIPTS_DIR"/*.py; do
    [[ -f "$script" ]] || continue
    [[ "$(basename "$script")" == "help-devtools.sh" ]] && continue

    metadata=$(extract_metadata "$script" 2>/dev/null) || continue

    IFS='|' read -r name desc cat usage <<< "$metadata"

    if [[ -n "$cat" ]]; then
        TOOLS_BY_CATEGORY["$cat"]+="$name|$desc|$usage"$'\n'
    fi
done

# Output as JSON
if $OUTPUT_JSON; then
    echo "{"
    first_cat=true
    for category in $(echo "${!TOOLS_BY_CATEGORY[@]}" | tr ' ' '\n' | sort); do
        $first_cat || echo ","
        first_cat=false
        echo "  \"$category\": ["
        first_tool=true
        while IFS='|' read -r name desc usage; do
            [[ -z "$name" ]] && continue
            $first_tool || echo ","
            first_tool=false
            echo "    {\"name\": \"$name\", \"description\": \"$desc\", \"usage\": \"$usage\"}"
        done <<< "${TOOLS_BY_CATEGORY[$category]}"
        echo -n "  ]"
    done
    echo
    echo "}"
    exit 0
fi

# Output as formatted text
echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║                    DevTools Command Reference                  ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Sort categories and display
for category in $(echo "${!TOOLS_BY_CATEGORY[@]}" | tr ' ' '\n' | sort); do
    # Category header
    case $category in
        git)    echo -e "${GREEN}Git Tools:${NC}" ;;
        github) echo -e "${GREEN}GitHub Tools:${NC}" ;;
        system) echo -e "${GREEN}System Tools:${NC}" ;;
        *)      echo -e "${GREEN}${category^} Tools:${NC}" ;;
    esac

    # Tools in category
    while IFS='|' read -r name desc usage; do
        [[ -z "$name" ]] && continue
        printf "  ${CYAN}%-22s${NC} %s\n" "$name" "$desc"
    done <<< "${TOOLS_BY_CATEGORY[$category]}"
    echo ""
done

echo -e "${YELLOW}Usage:${NC} <tool-name> --help for detailed options"
echo ""
