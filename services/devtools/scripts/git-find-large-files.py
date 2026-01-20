#!/usr/bin/env python3
# @name: git-find-large-files
# @description: Find large files in git history
# @category: git
# @usage: git-find-large-files.py [--size <min-size>] [--top <n>]
"""
git-find-large-files.py - Large File Finder
Findet große Dateien in der Git-History zur Vorbereitung auf LFS-Migration
oder History-Bereinigung.
"""

import sys
import subprocess
import argparse
from typing import List, Dict, Optional, Tuple
import os
import re

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'


def run_cmd(args: List[str], capture: bool = True) -> Optional[str]:
    """Run command."""
    try:
        if capture:
            result = subprocess.run(args, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(args, check=True)
            return None
    except subprocess.CalledProcessError as e:
        if capture:
            return None
        raise


def is_git_repo() -> bool:
    """Check if current directory is a git repo."""
    return os.path.isdir(".git")


def parse_size(size_str: str) -> int:
    """Parse size string like '10M' to bytes."""
    size_str = size_str.upper().strip()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$', size_str)
    if not match:
        return int(size_str)

    value = float(match.group(1))
    unit = match.group(2)

    multipliers = {'': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
    return int(value * multipliers.get(unit, 1))


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if size_bytes != int(size_bytes) else f"{int(size_bytes)} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_all_objects() -> List[Tuple[str, int, str]]:
    """Get all objects with their sizes using git rev-list and cat-file."""
    # Get all blob objects
    output = run_cmd([
        "git", "rev-list", "--objects", "--all"
    ])
    if not output:
        return []

    objects = []
    for line in output.split('\n'):
        parts = line.split(' ', 1)
        if len(parts) >= 1:
            sha = parts[0]
            path = parts[1] if len(parts) > 1 else ""
            objects.append((sha, path))

    # Get sizes using batch-check
    if not objects:
        return []

    shas = '\n'.join(obj[0] for obj in objects)
    result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input=shas,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return []

    sizes = {}
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "blob":
            sizes[parts[0]] = int(parts[2])

    # Combine objects with sizes
    result_list = []
    for sha, path in objects:
        if sha in sizes:
            result_list.append((sha, sizes[sha], path))

    return result_list


def find_large_files(min_size: int = 0, top_n: int = 50) -> List[Dict]:
    """Find large files in git history."""
    objects = get_all_objects()

    # Filter and sort
    large_files = [
        {"sha": sha, "size": size, "path": path}
        for sha, size, path in objects
        if size >= min_size and path
    ]

    # Sort by size descending
    large_files.sort(key=lambda x: -x["size"])

    # Deduplicate by path, keeping largest
    seen_paths = {}
    deduplicated = []
    for f in large_files:
        path = f["path"]
        if path not in seen_paths or seen_paths[path]["size"] < f["size"]:
            seen_paths[path] = f

    deduplicated = sorted(seen_paths.values(), key=lambda x: -x["size"])

    return deduplicated[:top_n]


def get_file_extensions(files: List[Dict]) -> Dict[str, Dict]:
    """Group files by extension."""
    extensions = {}
    for f in files:
        path = f["path"]
        ext = os.path.splitext(path)[1].lower() or "(no extension)"

        if ext not in extensions:
            extensions[ext] = {"count": 0, "total_size": 0, "files": []}
        extensions[ext]["count"] += 1
        extensions[ext]["total_size"] += f["size"]
        extensions[ext]["files"].append(f)

    return extensions


def check_in_current(path: str) -> bool:
    """Check if file exists in current HEAD."""
    result = run_cmd(["git", "ls-files", "--", path])
    return result is not None and result != ""


def main():
    parser = argparse.ArgumentParser(
        description="Find large files in git history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find top 50 largest files
  git-find-large-files.py

  # Find files larger than 10MB
  git-find-large-files.py --size 10M

  # Find files larger than 1MB, top 100
  git-find-large-files.py --size 1M --top 100

  # Group by extension
  git-find-large-files.py --by-extension

  # Show only history (deleted files)
  git-find-large-files.py --history-only

  # Export as JSON
  git-find-large-files.py --json

  # Generate LFS patterns
  git-find-large-files.py --lfs-patterns
        """
    )

    parser.add_argument(
        "--size", "-s",
        default="100K",
        help="Minimum file size (default: 100K)"
    )
    parser.add_argument(
        "--top", "-n",
        type=int,
        default=50,
        help="Number of files to show (default: 50)"
    )
    parser.add_argument(
        "--by-extension",
        action="store_true",
        help="Group results by file extension"
    )
    parser.add_argument(
        "--history-only",
        action="store_true",
        help="Show only files not in current HEAD"
    )
    parser.add_argument(
        "--lfs-patterns",
        action="store_true",
        help="Generate .gitattributes patterns for LFS"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Check if in git repo
    if not is_git_repo():
        print(f"{RED}[ERROR] Not in a git repository{NC}")
        sys.exit(1)

    min_size = parse_size(args.size)

    # Header
    if not args.json:
        print()
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print(f"{BOLD}{CYAN}|                   Large File Finder                           |{NC}")
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print()
        print(f"Scanning git history for files >= {format_size(min_size)}...")
        print()

    # Find large files
    files = find_large_files(min_size, args.top * 2)  # Get more to filter

    if not files:
        if not args.json:
            print(f"{GREEN}No files found >= {format_size(min_size)}{NC}")
        else:
            print("[]")
        return

    # Filter history-only
    if args.history_only:
        files = [f for f in files if not check_in_current(f["path"])]

    files = files[:args.top]

    # JSON output
    if args.json:
        import json
        print(json.dumps(files, indent=2))
        return

    # LFS patterns
    if args.lfs_patterns:
        extensions = get_file_extensions(files)
        print("# Add to .gitattributes for LFS tracking:")
        print()
        for ext, data in sorted(extensions.items(), key=lambda x: -x[1]["total_size"]):
            if ext != "(no extension)":
                print(f"*{ext} filter=lfs diff=lfs merge=lfs -text")
        return

    # By extension
    if args.by_extension:
        extensions = get_file_extensions(files)
        print(f"{BOLD}Large files by extension:{NC}")
        print()

        for ext, data in sorted(extensions.items(), key=lambda x: -x[1]["total_size"]):
            print(f"{CYAN}{ext}{NC}: {data['count']} files, {format_size(data['total_size'])} total")
            for f in data["files"][:5]:
                in_head = "current" if check_in_current(f["path"]) else "history"
                print(f"    {f['path']} ({format_size(f['size'])}) [{in_head}]")
            if len(data["files"]) > 5:
                print(f"    {DIM}... and {len(data['files']) - 5} more{NC}")
            print()
        return

    # Default: list files
    print(f"{BOLD}Largest files in git history:{NC}")
    print()

    total_size = 0
    for i, f in enumerate(files, 1):
        size_str = format_size(f["size"])
        in_head = check_in_current(f["path"])
        status = f"{GREEN}current{NC}" if in_head else f"{YELLOW}history{NC}"

        # Color by size
        if f["size"] > 100 * 1024 * 1024:  # > 100MB
            size_color = RED
        elif f["size"] > 10 * 1024 * 1024:  # > 10MB
            size_color = YELLOW
        else:
            size_color = NC

        print(f"  {i:3}. {size_color}{size_str:>10}{NC}  {f['path']} [{status}]")
        total_size += f["size"]

    print()
    print(f"Total: {format_size(total_size)} in {len(files)} files")
    print()

    # Suggestions
    history_files = [f for f in files if not check_in_current(f["path"])]
    if history_files:
        print(f"{BOLD}Suggestions:{NC}")
        print(f"  - {len(history_files)} files only in history can be removed with git-filter-repo")
        print(f"  - Use --lfs-patterns to generate LFS tracking rules")
        print()


if __name__ == "__main__":
    main()
