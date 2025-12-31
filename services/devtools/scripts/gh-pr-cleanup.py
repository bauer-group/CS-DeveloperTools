#!/usr/bin/env python3
"""
gh-pr-cleanup.py - Clean Up Stale Pull Requests and Branches
Räumt alte PRs und verwaiste Branches auf.
"""

import sys
import json
import subprocess
import argparse
from datetime import datetime, timedelta
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


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse ISO date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_prs(repo: str, state: str = "open") -> List[Dict]:
    """Get pull requests for a repository."""
    output = run_gh([
        "pr", "list", "-R", repo,
        "--state", state,
        "--json", "number,title,author,createdAt,updatedAt,headRefName,isDraft,mergeable",
        "--limit", "500"
    ])
    if not output:
        return []
    return json.loads(output)


def get_branches(repo: str) -> List[Dict]:
    """Get all branches for a repository."""
    output = run_gh([
        "api", f"repos/{repo}/branches",
        "--paginate",
        "-q", '.[] | {name: .name, protected: .protected}'
    ])
    if not output:
        return []

    branches = []
    for line in output.strip().split("\n"):
        if line:
            branches.append(json.loads(line))
    return branches


def get_merged_branches(repo: str) -> List[str]:
    """Get branches that have been merged."""
    # Get PRs that were merged
    output = run_gh([
        "pr", "list", "-R", repo,
        "--state", "merged",
        "--json", "headRefName",
        "--limit", "500"
    ])
    if not output:
        return []

    prs = json.loads(output)
    return list(set(pr["headRefName"] for pr in prs))


def close_pr(repo: str, pr_number: int, comment: Optional[str] = None, dry_run: bool = False) -> bool:
    """Close a pull request."""
    if dry_run:
        return True

    try:
        args = ["pr", "close", str(pr_number), "-R", repo]
        if comment:
            args.extend(["--comment", comment])
        run_gh(args, capture=False)
        return True
    except subprocess.CalledProcessError:
        return False


def delete_branch(repo: str, branch: str, dry_run: bool = False) -> bool:
    """Delete a branch."""
    if dry_run:
        return True

    try:
        run_gh(["api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{branch}"])
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Clean up stale pull requests and branches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List stale PRs (not updated in 30 days)
  gh-pr-cleanup.py myorg/myrepo --list --stale-days 30

  # Close stale PRs with comment
  gh-pr-cleanup.py myorg/myrepo --close-stale --stale-days 60 \\
    --comment "Closing due to inactivity"

  # List merged branches that can be deleted
  gh-pr-cleanup.py myorg/myrepo --list-merged-branches

  # Delete merged branches
  gh-pr-cleanup.py myorg/myrepo --delete-merged-branches

  # Close draft PRs older than 90 days
  gh-pr-cleanup.py myorg/myrepo --close-drafts --stale-days 90

  # Full cleanup (dry run)
  gh-pr-cleanup.py myorg/myrepo --close-stale --delete-merged-branches --dry-run
        """
    )

    parser.add_argument(
        "repo",
        help="Repository (owner/name)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List stale PRs without closing"
    )
    parser.add_argument(
        "--list-merged-branches",
        action="store_true",
        help="List branches from merged PRs"
    )
    parser.add_argument(
        "--close-stale",
        action="store_true",
        help="Close stale PRs"
    )
    parser.add_argument(
        "--close-drafts",
        action="store_true",
        help="Close stale draft PRs"
    )
    parser.add_argument(
        "--delete-merged-branches",
        action="store_true",
        help="Delete branches from merged PRs"
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=30,
        help="Days without update to consider stale (default: 30)"
    )
    parser.add_argument(
        "--comment",
        help="Comment to add when closing PRs"
    )
    parser.add_argument(
        "--exclude-authors",
        help="Comma-separated list of authors to exclude"
    )
    parser.add_argument(
        "--exclude-labels",
        help="Comma-separated list of labels to exclude"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be done"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation"
    )

    args = parser.parse_args()

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                  GitHub PR/Branch Cleanup                     ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    print(f"{CYAN}Repository:{NC} {args.repo}")
    print(f"{CYAN}Stale threshold:{NC} {args.stale_days} days")
    print()

    now = datetime.now().astimezone()
    stale_threshold = now - timedelta(days=args.stale_days)

    exclude_authors = set()
    if args.exclude_authors:
        exclude_authors = set(a.strip().lower() for a in args.exclude_authors.split(","))

    # List or close stale PRs
    if args.list or args.close_stale or args.close_drafts:
        print(f"Fetching open PRs...")
        prs = get_prs(args.repo, "open")
        print(f"Found {len(prs)} open PRs")
        print()

        stale_prs = []
        for pr in prs:
            updated = parse_date(pr.get("updatedAt", ""))
            if not updated:
                continue

            # Check if stale
            if updated > stale_threshold:
                continue

            # Check author exclusion
            author = pr.get("author", {}).get("login", "").lower()
            if author in exclude_authors:
                continue

            # Check draft filter
            if args.close_drafts and not pr.get("isDraft", False):
                continue

            days_stale = (now - updated).days
            stale_prs.append({**pr, "days_stale": days_stale})

        if not stale_prs:
            print(f"{GREEN}No stale PRs found{NC}")
        else:
            print(f"{BOLD}Stale PRs ({len(stale_prs)}):{NC}")
            print()

            for pr in stale_prs:
                draft = " [DRAFT]" if pr.get("isDraft") else ""
                author = pr.get("author", {}).get("login", "unknown")
                print(f"  #{pr['number']}: {pr['title'][:50]}...{draft}")
                print(f"      Author: {author}, Stale: {pr['days_stale']} days")
                print(f"      Branch: {pr['headRefName']}")

            print()

            if args.close_stale or args.close_drafts:
                if args.dry_run:
                    print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
                    print(f"Would close {len(stale_prs)} PRs")
                else:
                    if not args.yes:
                        response = input(f"Close {len(stale_prs)} stale PRs? (yes/N): ")
                        if response.lower() != "yes":
                            print("Aborted.")
                            sys.exit(0)

                    closed = 0
                    for pr in stale_prs:
                        if close_pr(args.repo, pr["number"], args.comment, args.dry_run):
                            print(f"{GREEN}✓{NC} Closed #{pr['number']}")
                            closed += 1
                        else:
                            print(f"{RED}✗{NC} Failed #{pr['number']}")

                    print()
                    print(f"{GREEN}✓ {closed} PRs closed{NC}")

    # List or delete merged branches
    if args.list_merged_branches or args.delete_merged_branches:
        print()
        print(f"Fetching branches...")

        all_branches = get_branches(args.repo)
        merged_branch_names = get_merged_branches(args.repo)

        # Filter to branches that exist and are not protected
        deletable = []
        protected_branches = {"main", "master", "develop", "development", "staging", "production"}

        for branch in all_branches:
            name = branch["name"]
            if name in merged_branch_names and name not in protected_branches:
                if not branch.get("protected", False):
                    deletable.append(name)

        if not deletable:
            print(f"{GREEN}No merged branches to delete{NC}")
        else:
            print(f"{BOLD}Merged branches ({len(deletable)}):{NC}")
            print()

            for branch in deletable[:20]:
                print(f"  - {branch}")
            if len(deletable) > 20:
                print(f"  ... and {len(deletable) - 20} more")

            print()

            if args.delete_merged_branches:
                if args.dry_run:
                    print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
                    print(f"Would delete {len(deletable)} branches")
                else:
                    if not args.yes:
                        response = input(f"Delete {len(deletable)} merged branches? (yes/N): ")
                        if response.lower() != "yes":
                            print("Aborted.")
                            sys.exit(0)

                    deleted = 0
                    for branch in deletable:
                        if delete_branch(args.repo, branch, args.dry_run):
                            print(f"{GREEN}✓{NC} Deleted {branch}")
                            deleted += 1
                        else:
                            print(f"{RED}✗{NC} Failed {branch}")

                    print()
                    print(f"{GREEN}✓ {deleted} branches deleted{NC}")

    print()


if __name__ == "__main__":
    main()
