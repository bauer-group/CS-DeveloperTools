#!/bin/bash
# =============================================================================
# git-lfs-migrate.sh - Git LFS Migration Tool
# Migriert Repositories zu Git LFS für bessere Handhabung von Binärdateien
# =============================================================================

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Default values
DRY_RUN=false
AUTO_COMMIT=false
INCLUDE_HISTORY=false
CUSTOM_PATTERNS=()

usage() {
    echo ""
    echo -e "${BOLD}${BLUE}git-lfs-migrate.sh${NC} - Git LFS Migration Tool"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  git-lfs-migrate.sh [OPTIONS]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -d, --dry-run         Show what would be done without making changes"
    echo "  -y, --yes             Auto-commit without prompting"
    echo "  -H, --history         Migrate existing files in history (requires git-lfs-migrate)"
    echo "  -p, --pattern PAT     Add custom pattern to track (can be used multiple times)"
    echo "  -l, --list            List currently tracked LFS patterns"
    echo "  -s, --status          Show LFS status and tracked files"
    echo "  -h, --help            Show this help message"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  git-lfs-migrate.sh                    # Interactive migration"
    echo "  git-lfs-migrate.sh --dry-run          # Preview changes"
    echo "  git-lfs-migrate.sh -y                 # Auto-commit"
    echo "  git-lfs-migrate.sh -p '*.data'        # Add custom pattern"
    echo ""
}

# Prüfen ob wir in einem Git-Repository sind
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}[ERROR] Not a git repository${NC}"
        exit 1
    fi
}

# Git LFS Installation prüfen
check_lfs_installed() {
    if ! command -v git-lfs &> /dev/null; then
        echo -e "${RED}[ERROR] Git LFS is not installed${NC}"
        echo "Install with: apk add git-lfs (Alpine) or apt install git-lfs (Debian)"
        exit 1
    fi
}

# LFS Status anzeigen
show_status() {
    echo ""
    echo -e "${BOLD}${CYAN}═══ Git LFS Status ═══${NC}"
    echo ""

    # LFS Version
    echo -e "${YELLOW}Version:${NC}"
    git lfs version
    echo ""

    # Tracked patterns
    echo -e "${YELLOW}Tracked Patterns (.gitattributes):${NC}"
    if [ -f .gitattributes ]; then
        grep "filter=lfs" .gitattributes 2>/dev/null | sed 's/ filter=lfs.*//' | while read -r pattern; do
            echo "  $pattern"
        done
    else
        echo "  (no .gitattributes file)"
    fi
    echo ""

    # LFS files in repo
    echo -e "${YELLOW}LFS Files in Repository:${NC}"
    LFS_FILES=$(git lfs ls-files 2>/dev/null | wc -l)
    echo "  $LFS_FILES file(s) tracked by LFS"

    if [ "$LFS_FILES" -gt 0 ]; then
        echo ""
        git lfs ls-files 2>/dev/null | head -10
        if [ "$LFS_FILES" -gt 10 ]; then
            echo "  ... and $((LFS_FILES - 10)) more"
        fi
    fi
    echo ""
}

# Tracked patterns auflisten
list_patterns() {
    echo ""
    echo -e "${BOLD}${CYAN}═══ Git LFS Tracked Patterns ═══${NC}"
    echo ""

    if [ -f .gitattributes ]; then
        grep "filter=lfs" .gitattributes 2>/dev/null | while read -r line; do
            pattern=$(echo "$line" | awk '{print $1}')
            echo "  $pattern"
        done
    else
        echo "  No patterns tracked (no .gitattributes file)"
    fi
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -y|--yes)
            AUTO_COMMIT=true
            shift
            ;;
        -H|--history)
            INCLUDE_HISTORY=true
            shift
            ;;
        -p|--pattern)
            CUSTOM_PATTERNS+=("$2")
            shift 2
            ;;
        -l|--list)
            check_git_repo
            list_patterns
            exit 0
            ;;
        -s|--status)
            check_git_repo
            show_status
            exit 0
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

# Checks
check_git_repo
check_lfs_installed

# Standard-Dateierweiterungen für LFS
declare -a BIN_EXTENSIONS=(
    # ═══ Microsoft Office ═══
    "*.doc" "*.docx" "*.dot" "*.dotx" "*.docm"
    "*.xls" "*.xlsx" "*.xlsm" "*.xlt" "*.xltx" "*.xlsb"
    "*.ppt" "*.pptx" "*.pps" "*.ppsx" "*.pptm"
    "*.vsd" "*.vsdx" "*.vsdm"
    "*.pub" "*.pubx"
    "*.msg" "*.pst" "*.ost"
    "*.accdb" "*.accde" "*.mdb"

    # ═══ OpenOffice / LibreOffice ═══
    "*.odt" "*.ott" "*.odm"
    "*.ods" "*.ots"
    "*.odp" "*.otp"
    "*.odg" "*.otg"
    "*.odb" "*.odf"

    # ═══ Installer / Packaging ═══
    "*.msi" "*.msp" "*.mst" "*.msix"
    "*.cab" "*.appx"
    "*.deb" "*.rpm" "*.pkg" "*.dmg"
    "*.snap" "*.flatpak"

    # ═══ Archive formats ═══
    "*.zip" "*.7z" "*.rar" "*.tar"
    "*.gz" "*.tgz" "*.bz2" "*.xz" "*.lz" "*.lzma"
    "*.tar.gz" "*.tar.bz2" "*.tar.xz"

    # ═══ Images ═══
    "*.png" "*.jpg" "*.jpeg" "*.gif" "*.webp"
    "*.tiff" "*.tif" "*.bmp" "*.ico" "*.icns"
    "*.psd" "*.ai" "*.eps" "*.svgz"
    "*.raw" "*.cr2" "*.nef" "*.orf" "*.arw"
    "*.heic" "*.heif"

    # ═══ Audio ═══
    "*.mp3" "*.wav" "*.ogg" "*.flac" "*.aac"
    "*.wma" "*.m4a" "*.aiff" "*.ape"

    # ═══ Video ═══
    "*.mp4" "*.mov" "*.avi" "*.mkv" "*.webm"
    "*.wmv" "*.flv" "*.m4v" "*.mpeg" "*.mpg"
    "*.3gp" "*.ogv"

    # ═══ Fonts ═══
    "*.ttf" "*.otf" "*.woff" "*.woff2" "*.eot"

    # ═══ 3D / CAD ═══
    "*.obj" "*.fbx" "*.blend" "*.3ds" "*.dae"
    "*.stl" "*.step" "*.stp" "*.iges" "*.igs"
    "*.dwg" "*.dxf"

    # ═══ Generic binaries ═══
    "*.bin" "*.dat" "*.dll" "*.exe" "*.so" "*.dylib"
    "*.iso" "*.img" "*.vhd" "*.vhdx" "*.vmdk"
    "*.a" "*.lib" "*.o"

    # ═══ Data formats ═══
    "*.sqlite" "*.sqlite3" "*.db"
    "*.pdf"
    "*.parquet" "*.avro"

    # ═══ Game / Unity / Unreal ═══
    "*.unity" "*.unitypackage" "*.asset"
    "*.uasset" "*.umap"

    # ═══ Machine Learning ═══
    "*.h5" "*.hdf5" "*.onnx" "*.pb"
    "*.pt" "*.pth" "*.pkl" "*.pickle"
    "*.safetensors"
)

echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║                    Git LFS Migration Tool                      ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
echo -e "${CYAN}Repository:${NC} $REPO_NAME"
echo ""

# ═══ Step 1: Initialize LFS ═══
echo -e "${BOLD}${GREEN}═══ Step 1: Initialize Git LFS ═══${NC}"
if [ "$DRY_RUN" = false ]; then
    git lfs install --skip-repo 2>/dev/null || git lfs install
    echo -e "${GREEN}✓ Git LFS initialized${NC}"
else
    echo -e "${YELLOW}Would initialize Git LFS${NC}"
fi
echo ""

# ═══ Step 2: Track patterns ═══
echo -e "${BOLD}${GREEN}═══ Step 2: Track Binary Patterns ═══${NC}"

# Add custom patterns first
if [ ${#CUSTOM_PATTERNS[@]} -gt 0 ]; then
    echo -e "${CYAN}Custom patterns:${NC}"
    for pattern in "${CUSTOM_PATTERNS[@]}"; do
        if [ "$DRY_RUN" = false ]; then
            git lfs track "$pattern" 2>/dev/null
        fi
        echo "  ✓ $pattern"
    done
    echo ""
fi

# Standard patterns
TRACKED_COUNT=0
SKIPPED_COUNT=0

echo -e "${CYAN}Standard patterns:${NC}"
for ext in "${BIN_EXTENSIONS[@]}"; do
    # Check if already tracked
    if [ -f .gitattributes ] && grep -q "^${ext//\*/\\*} " .gitattributes 2>/dev/null; then
        ((SKIPPED_COUNT++))
        continue
    fi

    if [ "$DRY_RUN" = false ]; then
        git lfs track "$ext" 2>/dev/null
    fi
    ((TRACKED_COUNT++))
done

echo "  Added $TRACKED_COUNT new patterns"
if [ "$SKIPPED_COUNT" -gt 0 ]; then
    echo "  Skipped $SKIPPED_COUNT already tracked patterns"
fi
echo ""

# ═══ Step 3: Stage .gitattributes ═══
echo -e "${BOLD}${GREEN}═══ Step 3: Stage .gitattributes ═══${NC}"
if [ "$DRY_RUN" = false ]; then
    git add .gitattributes
    echo -e "${GREEN}✓ .gitattributes staged${NC}"
else
    echo -e "${YELLOW}Would stage .gitattributes${NC}"
fi
echo ""

# ═══ Step 4: Check for existing files to migrate ═══
echo -e "${BOLD}${GREEN}═══ Step 4: Check Existing Files ═══${NC}"

# Find files that match LFS patterns but aren't in LFS
MATCHING_FILES=0
if [ -f .gitattributes ]; then
    while IFS= read -r pattern; do
        pattern=$(echo "$pattern" | awk '{print $1}')
        # Convert glob to find pattern
        find_pattern="${pattern//\*\*/}"
        find_pattern="${find_pattern//\*/}"

        count=$(git ls-files "$pattern" 2>/dev/null | wc -l)
        if [ "$count" -gt 0 ]; then
            MATCHING_FILES=$((MATCHING_FILES + count))
        fi
    done < <(grep "filter=lfs" .gitattributes 2>/dev/null)
fi

if [ "$MATCHING_FILES" -gt 0 ]; then
    echo -e "${YELLOW}Found $MATCHING_FILES existing file(s) matching LFS patterns${NC}"
    echo ""

    if [ "$DRY_RUN" = false ]; then
        if [ "$AUTO_COMMIT" = true ]; then
            MIGRATE="y"
        else
            read -p "Migrate existing files to LFS? (y/N): " MIGRATE
        fi

        if [[ "$MIGRATE" =~ ^[yY]$ ]]; then
            echo -e "${CYAN}Migrating files...${NC}"
            git add --renormalize .
            echo -e "${GREEN}✓ Files migrated${NC}"
        else
            echo -e "${YELLOW}Migration skipped${NC}"
        fi
    else
        echo -e "${YELLOW}Would prompt to migrate existing files${NC}"
    fi
else
    echo -e "${GREEN}✓ No existing files need migration${NC}"
fi
echo ""

# ═══ Step 5: Commit ═══
echo -e "${BOLD}${GREEN}═══ Step 5: Commit Changes ═══${NC}"

if [ "$DRY_RUN" = false ]; then
    # Check if there are changes to commit
    if git diff --cached --quiet; then
        echo -e "${YELLOW}No changes to commit${NC}"
    else
        if [ "$AUTO_COMMIT" = true ]; then
            COMMIT="y"
        else
            read -p "Commit changes? (y/N): " COMMIT
        fi

        if [[ "$COMMIT" =~ ^[yY]$ ]]; then
            git commit -m "chore: enable Git LFS for binary files

Track common binary formats including:
- Office documents (Microsoft, OpenOffice)
- Images, audio, video
- Archives and installers
- Fonts, 3D models, CAD files
- Data files and ML models"
            echo -e "${GREEN}✓ Changes committed${NC}"
        else
            echo -e "${YELLOW}Commit skipped (changes are staged)${NC}"
        fi
    fi
else
    echo -e "${YELLOW}Would commit changes${NC}"
fi
echo ""

# ═══ Summary ═══
echo -e "${BOLD}${GREEN}═══ Summary ═══${NC}"
echo -e "Patterns tracked: ${CYAN}$((TRACKED_COUNT + ${#CUSTOM_PATTERNS[@]}))${NC}"

if [ -f .gitattributes ]; then
    TOTAL_PATTERNS=$(grep -c "filter=lfs" .gitattributes 2>/dev/null || echo "0")
    echo -e "Total LFS patterns: ${CYAN}$TOTAL_PATTERNS${NC}"
fi

echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "  1. Review changes: git status"
echo "  2. Push to remote: git push"
echo ""
echo -e "${GREEN}✓ Git LFS migration complete!${NC}"
echo ""
