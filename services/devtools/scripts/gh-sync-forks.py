#!/usr/bin/env python3
# @name: gh-sync-forks
# @description: Sync forked repositories with upstream
# @category: github
# @usage: gh-sync-forks.py [--repo <name>] [--all]
"""
gh-sync-forks.py - Sync Forked Repositories with Upstream
Synchronisiert geforkten Repositories mit ihrem Upstream.
"""

import sys
import json
import subprocess
import argparse
from typing import List, Dict, Optional

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'


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


def get_forks(owner: Optional[str] = None, limit: int = 200) -> List[Dict]:
    """Get list of forked repositories."""
    args = ["repo", "list"]
    if owner:
        args.append(owner)

    args.extend([
        "--fork",
        "--json", "name,nameWithOwner,parent,defaultBranchRef",
        "--limit", str(limit)
    ])

    output = run_gh(args)
    if not output:
        return []

    repos = json.loads(output)
    # Filter to only include actual forks with parent info
    return [r for r in repos if r.get("parent")]


def get_fork_status(repo: str) -> Dict:
    """Get sync status of a fork."""
    output = run_gh(["api", f"repos/{repo}"])
    if not output:
        return {}

    data = json.loads(output)
    parent = data.get("parent", {})

    if not parent:
        return {"error": "Not a fork"}

    # Get branch comparison
    default_branch = data.get("default_branch", "main")
    parent_full = parent.get("full_name", "")

    # Compare commits
    compare_output = run_gh([
        "api", f"repos/{repo}/compare/{parent_full.replace('/', ':')}:{default_branch}...{default_branch}"
    ])

    if compare_output:
        compare_data = json.loads(compare_output)
        behind = compare_data.get("behind_by", 0)
        ahead = compare_data.get("ahead_by", 0)
    else:
        behind = 0
        ahead = 0

    return {
        "parent": parent_full,
        "parent_branch": parent.get("default_branch", "main"),
        "behind": behind,
        "ahead": ahead,
        "default_branch": default_branch
    }


def sync_fork(repo: str, branch: Optional[str] = None, dry_run: bool = False) -> bool:
    """Sync a fork with its upstream."""
    if dry_run:
        return True

    try:
        args = ["repo", "sync", repo]
        if branch:
            args.extend(["--branch", branch])

        run_gh(args, capture=False)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync forked repositories with upstream",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all forks and their sync status
  gh-sync-forks.py --list

  # List forks for specific owner
  gh-sync-forks.py -o myuser --list

  # Sync a specific fork
  gh-sync-forks.py myuser/my-fork

  # Sync all forks
  gh-sync-forks.py --all

  # Sync only forks that are behind
  gh-sync-forks.py --behind

  # Dry run
  gh-sync-forks.py --all --dry-run
        """
    )

    parser.add_argument(
        "repo",
        nargs="?",
        help="Specific fork to sync (owner/name)"
    )
    parser.add_argument(
        "-o", "--owner",
        help="Owner (user or org) to list forks from"
    )
    parser.add_argument(
        "-b", "--branch",
        help="Specific branch to sync"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List forks and their sync status"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Sync all forks"
    )
    parser.add_argument(
        "--behind",
        action="store_true",
        help="Only sync forks that are behind upstream"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be synced"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max forks to process (default: 200)"
    )

    args = parser.parse_args()

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                  GitHub Fork Synchronizer                     ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    # Single repo mode
    if args.repo:
        print(f"Syncing: {args.repo}")
        print()

        status = get_fork_status(args.repo)
        if "error" in status:
            print(f"{RED}[ERROR] {status['error']}{NC}")
            sys.exit(1)

        print(f"  Parent: {status['parent']}")
        print(f"  Behind: {status['behind']} commits")
        print(f"  Ahead: {status['ahead']} commits")
        print()

        if args.dry_run:
            print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
            print(f"Would sync {args.repo} with {status['parent']}")
        else:
            if sync_fork(args.repo, args.branch):
                print(f"{GREEN}✓ Fork synced successfully{NC}")
            else:
                print(f"{RED}✗ Failed to sync fork{NC}")
                sys.exit(1)
        print()
        sys.exit(0)

    # Get all forks
    print(f"Fetching forks...")
    forks = get_forks(owner=args.owner, limit=args.limit)
    print(f"Found {len(forks)} forks")
    print()

    if not forks:
        print(f"{YELLOW}No forks found{NC}")
        sys.exit(0)

    # List mode
    if args.list:
        print(f"{BOLD}Fork Status:{NC}")
        print()

        for fork in forks:
            name = fork["nameWithOwner"]
            parent = fork.get("parent", {}).get("nameWithOwner", "unknown")

            status = get_fork_status(name)
            behind = status.get("behind", "?")
            ahead = status.get("ahead", "?")

            if behind == 0:
                status_icon = f"{GREEN}✓{NC}"
                status_text = "up to date"
            elif behind == "?":
                status_icon = f"{YELLOW}?{NC}"
                status_text = "unknown"
            else:
                status_icon = f"{YELLOW}↓{NC}"
                status_text = f"{behind} behind"

            if ahead and ahead != "?" and ahead > 0:
                status_text += f", {ahead} ahead"

            print(f"  {status_icon} {name}")
            print(f"      ← {parent} ({status_text})")

        print()
        sys.exit(0)

    # Sync mode
    if not args.all and not args.behind:
        print(f"{RED}[ERROR] Specify --all, --behind, or a specific repo{NC}")
        sys.exit(1)

    if args.dry_run:
        print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
        print()

    # Sync forks
    synced = 0
    skipped = 0
    failed = 0

    for fork in forks:
        name = fork["nameWithOwner"]

        if args.behind:
            status = get_fork_status(name)
            behind = status.get("behind", 0)
            if behind == 0:
                skipped += 1
                continue

        print(f"{CYAN}→{NC} {name}...", end=" ")

        if args.dry_run:
            print(f"{GREEN}would sync{NC}")
            synced += 1
        elif sync_fork(name, args.branch):
            print(f"{GREEN}✓ synced{NC}")
            synced += 1
        else:
            print(f"{RED}✗ failed{NC}")
            failed += 1

    # Summary
    print()
    action = "would be " if args.dry_run else ""
    print(f"{GREEN}✓ {synced} forks {action}synced{NC}")
    if skipped:
        print(f"{YELLOW}○ {skipped} skipped (up to date){NC}")
    if failed:
        print(f"{RED}✗ {failed} failed{NC}")
    print()


if __name__ == "__main__":
    main()
