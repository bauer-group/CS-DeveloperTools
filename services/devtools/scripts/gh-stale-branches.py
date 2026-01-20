#!/usr/bin/env python3
# @name: gh-stale-branches
# @description: Find stale branches across organization repositories
# @category: github
# @usage: gh-stale-branches.py [-o <org>] [--days <n>] [--delete]
"""
gh-stale-branches.py - Stale Branch Finder
Findet und bereinigt veraltete Branches über alle Repositories einer Organisation.
"""

import sys
import json
import subprocess
import argparse
from typing import List, Dict, Optional
from datetime import datetime, timezone
import re

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Protected branch patterns
PROTECTED_PATTERNS = [
    r'^main$', r'^master$', r'^develop$', r'^dev$',
    r'^release/', r'^hotfix/', r'^production$', r'^staging$'
]


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


def get_org_repos(org: str) -> List[Dict]:
    """Get all non-archived repositories for an organization."""
    output = run_gh([
        "api", f"/orgs/{org}/repos",
        "--paginate",
        "-q", ".[] | select(.archived == false) | {name: .name, default_branch: .default_branch}"
    ])
    if not output:
        return []

    repos = []
    for line in output.strip().split('\n'):
        if line:
            repos.append(json.loads(line))
    return repos


def get_branches(org: str, repo: str) -> List[Dict]:
    """Get all branches for a repository with commit info."""
    output = run_gh([
        "api", f"repos/{org}/{repo}/branches",
        "--paginate",
        "-q", ".[] | {name: .name, sha: .commit.sha, protected: .protected}"
    ])
    if not output:
        return []

    branches = []
    for line in output.strip().split('\n'):
        if line:
            branches.append(json.loads(line))
    return branches


def get_commit_date(org: str, repo: str, sha: str) -> Optional[datetime]:
    """Get the date of a commit."""
    output = run_gh([
        "api", f"repos/{org}/{repo}/commits/{sha}",
        "-q", ".commit.committer.date"
    ])
    if not output:
        return None
    try:
        return datetime.fromisoformat(output.replace('Z', '+00:00'))
    except ValueError:
        return None


def is_protected_branch(name: str, default_branch: str) -> bool:
    """Check if branch name matches protected patterns."""
    if name == default_branch:
        return True
    for pattern in PROTECTED_PATTERNS:
        if re.match(pattern, name, re.IGNORECASE):
            return True
    return False


def delete_branch(org: str, repo: str, branch: str, dry_run: bool = True) -> bool:
    """Delete a branch from a repository."""
    if dry_run:
        return True

    import urllib.parse
    encoded_branch = urllib.parse.quote(branch, safe='')

    try:
        run_gh(["api", "-X", "DELETE", f"repos/{org}/{repo}/git/refs/heads/{encoded_branch}"])
        return True
    except Exception:
        return False


def days_ago(dt: datetime) -> int:
    """Calculate days since datetime."""
    now = datetime.now(timezone.utc)
    delta = now - dt
    return delta.days


def main():
    parser = argparse.ArgumentParser(
        description="Find stale branches across organization repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find branches older than 90 days
  gh-stale-branches.py

  # Find branches older than 30 days
  gh-stale-branches.py --days 30

  # Check specific repo
  gh-stale-branches.py --repo myrepo

  # Delete stale branches (dry run)
  gh-stale-branches.py --delete

  # Actually delete stale branches
  gh-stale-branches.py --delete --execute

  # Include all branches (ignore protected patterns)
  gh-stale-branches.py --include-protected

  # Export as JSON
  gh-stale-branches.py --json
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--repo",
        help="Only check specific repository"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Branches older than this are stale (default: 90)"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete stale branches"
    )
    parser.add_argument(
        "--include-protected",
        action="store_true",
        help="Include protected branch patterns"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete branches (default: dry run)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()
    dry_run = not args.execute

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    # Header
    if not args.json:
        print()
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print(f"{BOLD}{CYAN}|                   Stale Branch Finder                         |{NC}")
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print()

        if args.delete and dry_run:
            print(f"{YELLOW}[DRY RUN MODE]{NC} - No branches will be deleted")
            print("Use --execute to actually delete")
            print()

    # Get repositories
    if args.repo:
        repos = [{"name": args.repo, "default_branch": "main"}]
    else:
        if not args.json:
            print(f"Scanning repositories in {BOLD}{args.org}{NC}...")
        repos = get_org_repos(args.org)

    if not repos:
        print(f"{RED}[ERROR] No repositories found{NC}")
        sys.exit(1)

    if not args.json:
        print(f"  Found {len(repos)} repos")
        print(f"  Looking for branches older than {args.days} days")
        print()

    # Find stale branches
    all_stale = []
    total_branches = 0
    total_stale = 0
    deleted = 0

    for repo in repos:
        repo_name = repo["name"]
        default_branch = repo.get("default_branch", "main")

        branches = get_branches(args.org, repo_name)
        if not branches:
            continue

        repo_stale = []
        for branch in branches:
            total_branches += 1
            branch_name = branch["name"]

            # Skip protected branches
            if not args.include_protected:
                if branch.get("protected") or is_protected_branch(branch_name, default_branch):
                    continue

            # Get commit date
            commit_date = get_commit_date(args.org, repo_name, branch["sha"])
            if not commit_date:
                continue

            age = days_ago(commit_date)
            if age >= args.days:
                total_stale += 1
                stale_info = {
                    "repo": repo_name,
                    "branch": branch_name,
                    "age_days": age,
                    "last_commit": commit_date.isoformat()
                }
                repo_stale.append(stale_info)
                all_stale.append(stale_info)

        # Output for this repo
        if repo_stale and not args.json:
            print(f"{BOLD}{repo_name}{NC} ({len(repo_stale)} stale)")
            for s in repo_stale:
                age_color = RED if s["age_days"] > 180 else YELLOW
                print(f"  {age_color}{s['branch']}{NC} ({s['age_days']} days)")

                if args.delete:
                    if delete_branch(args.org, repo_name, s["branch"], dry_run):
                        if not dry_run:
                            print(f"    {RED}→ Deleted{NC}")
                            deleted += 1
            print()

    # JSON output
    if args.json:
        print(json.dumps({
            "org": args.org,
            "threshold_days": args.days,
            "total_branches": total_branches,
            "stale_count": total_stale,
            "stale_branches": all_stale
        }, indent=2))
        return

    # Summary
    print("=" * 60)
    print(f"{BOLD}Summary:{NC}")
    print(f"  Total branches scanned: {total_branches}")
    print(f"  Stale branches (>{args.days} days): {YELLOW}{total_stale}{NC}")
    if args.delete:
        print(f"  Deleted: {RED}{deleted}{NC}")
    print()

    if total_stale > 0 and not args.delete:
        print(f"Use {BOLD}--delete{NC} to remove stale branches")
        print()


if __name__ == "__main__":
    main()
