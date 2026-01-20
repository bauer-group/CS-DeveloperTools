#!/usr/bin/env python3
# @name: gh-repo-settings
# @description: Manage repository settings across organization
# @category: github
# @usage: gh-repo-settings.py [-o <org>] [--topic <topic>] [--execute]
"""
gh-repo-settings.py - Repository Settings Manager
Verwaltet Repository-Einstellungen über eine Organisation hinweg.
Unterstützt Filterung nach Topics, Namen und anderen Kriterien.
"""

import sys
import json
import subprocess
import argparse
import re
from typing import List, Dict, Optional, Set

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Preset configurations
PRESETS = {
    "standard": {
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
        "has_discussions": False,
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": True,
        "delete_branch_on_merge": True,
        "allow_auto_merge": True,
    },
    "minimal": {
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
        "has_discussions": False,
    },
    "full": {
        "has_issues": True,
        "has_wiki": True,
        "has_projects": True,
        "has_discussions": True,
        "allow_squash_merge": True,
        "allow_merge_commit": True,
        "allow_rebase_merge": True,
        "delete_branch_on_merge": True,
        "allow_auto_merge": True,
    },
    "secure": {
        "has_wiki": False,
        "allow_merge_commit": False,
        "delete_branch_on_merge": True,
        "allow_auto_merge": False,
        "allow_squash_merge": True,
        "allow_rebase_merge": False,
    },
}


def run_gh(args: List[str], capture: bool = True) -> Optional[str]:
    """Run GitHub CLI command."""
    cmd = ["gh"] + args
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=True)
            return None
    except subprocess.CalledProcessError as e:
        if capture:
            return None
        raise


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated."""
    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_org_repos(org: str, include_archived: bool = False) -> List[Dict]:
    """Get all repositories for an organization."""
    query = ".[] | {name: .name, archived: .archived, topics: .topics, visibility: .visibility}"
    output = run_gh([
        "api", f"/orgs/{org}/repos",
        "--paginate",
        "-q", query
    ])
    if not output:
        return []

    repos = []
    for line in output.strip().split('\n'):
        if line:
            repo = json.loads(line)
            if include_archived or not repo.get("archived", False):
                repos.append(repo)
    return repos


def get_repo_settings(org: str, repo: str) -> Optional[Dict]:
    """Get current repository settings."""
    output = run_gh(["api", f"repos/{org}/{repo}"])
    if not output:
        return None
    return json.loads(output)


def update_repo_settings(org: str, repo: str, settings: Dict, dry_run: bool = True) -> bool:
    """Update repository settings."""
    if dry_run:
        return True

    # Build API call with settings
    args = ["api", "-X", "PATCH", f"repos/{org}/{repo}"]
    for key, value in settings.items():
        if isinstance(value, bool):
            args.extend(["-F", f"{key}={str(value).lower()}"])
        else:
            args.extend(["-f", f"{key}={value}"])

    try:
        run_gh(args)
        return True
    except Exception:
        return False


def filter_repos(repos: List[Dict], topic: Optional[str] = None,
                 name_pattern: Optional[str] = None,
                 visibility: Optional[str] = None,
                 exclude_pattern: Optional[str] = None) -> List[Dict]:
    """Filter repositories by criteria."""
    filtered = repos

    if topic:
        filtered = [r for r in filtered if topic in r.get("topics", [])]

    if name_pattern:
        pattern = re.compile(name_pattern, re.IGNORECASE)
        filtered = [r for r in filtered if pattern.search(r["name"])]

    if exclude_pattern:
        pattern = re.compile(exclude_pattern, re.IGNORECASE)
        filtered = [r for r in filtered if not pattern.search(r["name"])]

    if visibility:
        filtered = [r for r in filtered if r.get("visibility") == visibility]

    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Manage repository settings across organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current settings for all repos
  gh-repo-settings.py --list

  # Apply standard preset to all repos
  gh-repo-settings.py --preset standard --execute

  # Apply settings to repos with specific topic
  gh-repo-settings.py --topic python --preset standard --execute

  # Apply settings to repos matching name pattern
  gh-repo-settings.py --name "cs-*" --preset minimal --execute

  # Disable wiki on all repos
  gh-repo-settings.py --set has_wiki=false --execute

  # Enable delete branch on merge
  gh-repo-settings.py --set delete_branch_on_merge=true --execute

  # Multiple settings
  gh-repo-settings.py --set has_wiki=false --set has_projects=false --execute

  # Show available presets
  gh-repo-settings.py --show-presets

Available presets: standard, minimal, full, secure
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--topic",
        help="Filter repos by topic"
    )
    parser.add_argument(
        "--name",
        help="Filter repos by name pattern (regex)"
    )
    parser.add_argument(
        "--exclude",
        help="Exclude repos matching pattern (regex)"
    )
    parser.add_argument(
        "--visibility",
        choices=["public", "private", "internal"],
        help="Filter by visibility"
    )
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        help="Apply predefined settings preset"
    )
    parser.add_argument(
        "--set",
        action="append",
        dest="settings",
        help="Set individual setting (key=value)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List current settings for matching repos"
    )
    parser.add_argument(
        "--show-presets",
        action="store_true",
        help="Show available presets and their settings"
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived repositories"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually apply changes (default: dry run)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()
    dry_run = not args.execute

    # Show presets
    if args.show_presets:
        print(f"\n{BOLD}Available Presets:{NC}\n")
        for name, settings in PRESETS.items():
            print(f"{CYAN}{name}:{NC}")
            for key, value in settings.items():
                print(f"  {key}: {GREEN if value else RED}{value}{NC}")
            print()
        return

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    # Header
    print()
    print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
    print(f"{BOLD}{CYAN}|              Repository Settings Manager                      |{NC}")
    print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
    print()

    if dry_run and not args.list:
        print(f"{YELLOW}[DRY RUN MODE]{NC} - No changes will be made")
        print("Use --execute to actually apply changes")
        print()

    # Get repositories
    print(f"Scanning repositories in {BOLD}{args.org}{NC}...")
    repos = get_org_repos(args.org, args.include_archived)

    if not repos:
        print(f"{RED}[ERROR] No repositories found{NC}")
        sys.exit(1)

    # Filter repositories
    filtered = filter_repos(
        repos,
        topic=args.topic,
        name_pattern=args.name,
        visibility=args.visibility,
        exclude_pattern=args.exclude
    )

    print(f"  Found {len(repos)} repos, {len(filtered)} match filters")
    print()

    if not filtered:
        print(f"{YELLOW}No repositories match the specified filters{NC}")
        sys.exit(0)

    # Determine settings to apply
    settings_to_apply = {}
    if args.preset:
        settings_to_apply.update(PRESETS[args.preset])
    if args.settings:
        for setting in args.settings:
            key, value = setting.split("=", 1)
            # Convert string to bool if needed
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            settings_to_apply[key] = value

    # List mode
    if args.list:
        print(f"{BOLD}Current Settings:{NC}")
        print()
        for repo in filtered:
            repo_name = repo["name"]
            settings = get_repo_settings(args.org, repo_name)
            if settings:
                print(f"{BOLD}{repo_name}{NC}")
                print(f"  has_issues: {settings.get('has_issues')}")
                print(f"  has_wiki: {settings.get('has_wiki')}")
                print(f"  has_projects: {settings.get('has_projects')}")
                print(f"  has_discussions: {settings.get('has_discussions')}")
                print(f"  allow_squash_merge: {settings.get('allow_squash_merge')}")
                print(f"  allow_merge_commit: {settings.get('allow_merge_commit')}")
                print(f"  allow_rebase_merge: {settings.get('allow_rebase_merge')}")
                print(f"  delete_branch_on_merge: {settings.get('delete_branch_on_merge')}")
                print(f"  allow_auto_merge: {settings.get('allow_auto_merge')}")
                print()
        return

    if not settings_to_apply:
        print(f"{YELLOW}No settings specified. Use --preset or --set{NC}")
        print("Use --show-presets to see available presets")
        sys.exit(1)

    # Show what will be applied
    print(f"{BOLD}Settings to apply:{NC}")
    for key, value in settings_to_apply.items():
        print(f"  {key}: {GREEN if value else RED}{value}{NC}")
    print()

    # Apply settings
    updated = 0
    failed = 0

    for repo in filtered:
        repo_name = repo["name"]
        print(f"{BOLD}→ {repo_name}{NC}", end=" ")

        if update_repo_settings(args.org, repo_name, settings_to_apply, dry_run):
            print(f"{GREEN}✓{NC}")
            updated += 1
        else:
            print(f"{RED}✗{NC}")
            failed += 1

    # Summary
    print()
    print("=" * 60)
    print(f"{BOLD}Summary:{NC}")
    print(f"  Repositories processed: {len(filtered)}")
    print(f"  Updated: {GREEN}{updated}{NC}")
    if failed > 0:
        print(f"  Failed: {RED}{failed}{NC}")
    print()

    if dry_run:
        print(f"Run with {BOLD}--execute{NC} to apply these changes.")
        print()


if __name__ == "__main__":
    main()
