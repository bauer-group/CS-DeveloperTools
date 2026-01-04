#!/usr/bin/env python3
# @name: gh-archive-repos
# @description: Archive GitHub repositories
# @category: github
# @usage: gh-archive-repos.py [--topic <topic>] [--older-than <days>]
"""
gh-archive-repos.py - GitHub Repository Archiver
Archiviert Repositories basierend auf verschiedenen Kriterien.
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


def get_repos(org: Optional[str] = None, include_archived: bool = False,
              limit: int = 500) -> List[Dict]:
    """Get list of repositories with details."""
    args = ["repo", "list"]

    if org:
        args.append(org)

    args.extend([
        "--json", "name,nameWithOwner,isArchived,pushedAt,updatedAt,createdAt,isEmpty,description",
        "--limit", str(limit)
    ])

    output = run_gh(args)
    if not output:
        return []

    repos = json.loads(output)

    if not include_archived:
        repos = [r for r in repos if not r.get("isArchived", False)]

    return repos


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse ISO date string."""
    if not date_str:
        return None
    try:
        # Handle different formats
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def archive_repo(repo: str, dry_run: bool = False) -> bool:
    """Archive a repository."""
    if dry_run:
        return True

    try:
        run_gh(["repo", "archive", repo, "--yes"])
        return True
    except subprocess.CalledProcessError:
        return False


def unarchive_repo(repo: str, dry_run: bool = False) -> bool:
    """Unarchive a repository."""
    if dry_run:
        return True

    try:
        run_gh(["repo", "unarchive", repo, "--yes"])
        return True
    except subprocess.CalledProcessError:
        return False


def filter_repos(repos: List[Dict], criteria: Dict) -> List[Dict]:
    """Filter repositories based on criteria."""
    filtered = []
    now = datetime.now().astimezone()

    for repo in repos:
        # Check inactivity (days since last push)
        if criteria.get("inactive_days"):
            pushed_at = parse_date(repo.get("pushedAt", ""))
            if pushed_at:
                days_inactive = (now - pushed_at).days
                if days_inactive < criteria["inactive_days"]:
                    continue
            else:
                # No push date, consider very old
                pass

        # Check if empty
        if criteria.get("empty_only") and not repo.get("isEmpty", False):
            continue

        # Check pattern
        if criteria.get("pattern"):
            import fnmatch
            if not fnmatch.fnmatch(repo["name"], criteria["pattern"]):
                continue

        # Check prefix
        if criteria.get("prefix"):
            if not repo["name"].startswith(criteria["prefix"]):
                continue

        # Check age (days since creation)
        if criteria.get("older_than_days"):
            created_at = parse_date(repo.get("createdAt", ""))
            if created_at:
                age_days = (now - created_at).days
                if age_days < criteria["older_than_days"]:
                    continue

        filtered.append(repo)

    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Archive GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Criteria Options:
  --inactive DAYS      Archive repos not pushed to in N days
  --empty              Archive only empty repositories
  --pattern PATTERN    Filter by name pattern (e.g., 'test-*')
  --prefix PREFIX      Filter by name prefix (e.g., 'deprecated-')
  --older-than DAYS    Archive repos older than N days

Examples:
  # List inactive repos (dry run)
  gh-archive-repos.py -o myorg --inactive 365 --dry-run

  # Archive empty repos
  gh-archive-repos.py -o myorg --empty

  # Archive repos matching pattern
  gh-archive-repos.py -o myorg --pattern "old-*" --dry-run

  # Archive repos inactive for 2 years
  gh-archive-repos.py -o myorg --inactive 730

  # Unarchive a specific repo
  gh-archive-repos.py myorg/myrepo --unarchive

  # List archived repos
  gh-archive-repos.py -o myorg --list-archived
        """
    )

    parser.add_argument(
        "repo",
        nargs="?",
        help="Specific repository (owner/name) to archive/unarchive"
    )
    parser.add_argument(
        "-o", "--org",
        help="Organization name for bulk operations"
    )
    parser.add_argument(
        "--inactive",
        type=int,
        metavar="DAYS",
        help="Archive repos inactive for N days"
    )
    parser.add_argument(
        "--empty",
        action="store_true",
        help="Archive only empty repositories"
    )
    parser.add_argument(
        "--pattern",
        help="Filter repos by name pattern"
    )
    parser.add_argument(
        "--prefix",
        help="Filter repos by name prefix"
    )
    parser.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help="Archive repos older than N days"
    )
    parser.add_argument(
        "--unarchive",
        action="store_true",
        help="Unarchive instead of archive"
    )
    parser.add_argument(
        "--list-archived",
        action="store_true",
        help="List archived repositories"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be archived"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Max repos to fetch (default: 500)"
    )

    args = parser.parse_args()

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                  GitHub Repository Archiver                   ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    # Single repo operation
    if args.repo:
        action = "Unarchive" if args.unarchive else "Archive"
        print(f"{action}: {args.repo}")
        print()

        if args.dry_run:
            print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
            print(f"Would {action.lower()}: {args.repo}")
        else:
            if args.unarchive:
                if unarchive_repo(args.repo):
                    print(f"{GREEN}✓ Repository unarchived{NC}")
                else:
                    print(f"{RED}[ERROR] Failed to unarchive{NC}")
                    sys.exit(1)
            else:
                if archive_repo(args.repo):
                    print(f"{GREEN}✓ Repository archived{NC}")
                else:
                    print(f"{RED}[ERROR] Failed to archive{NC}")
                    sys.exit(1)
        print()
        sys.exit(0)

    # Bulk operations require org
    if not args.org:
        print(f"{RED}[ERROR] Specify --org for bulk operations or provide a specific repo{NC}")
        sys.exit(1)

    # List archived repos
    if args.list_archived:
        print(f"Fetching archived repositories from {args.org}...")
        repos = get_repos(org=args.org, include_archived=True, limit=args.limit)
        archived = [r for r in repos if r.get("isArchived", False)]

        print(f"Found {len(archived)} archived repositories")
        print()

        for repo in archived:
            created = parse_date(repo.get("createdAt", ""))
            pushed = parse_date(repo.get("pushedAt", ""))
            created_str = created.strftime("%Y-%m-%d") if created else "unknown"
            pushed_str = pushed.strftime("%Y-%m-%d") if pushed else "never"

            print(f"  {CYAN}{repo['nameWithOwner']}{NC}")
            print(f"    Created: {created_str}, Last push: {pushed_str}")
            if repo.get("description"):
                print(f"    {repo['description'][:60]}")
            print()

        sys.exit(0)

    # Check that at least one criteria is specified
    if not any([args.inactive, args.empty, args.pattern, args.prefix, args.older_than]):
        print(f"{RED}[ERROR] Specify at least one filter criteria:{NC}")
        print("  --inactive DAYS, --empty, --pattern, --prefix, or --older-than")
        sys.exit(1)

    # Get repositories
    print(f"Fetching repositories from {args.org}...")
    repos = get_repos(org=args.org, include_archived=False, limit=args.limit)
    print(f"Found {len(repos)} active repositories")
    print()

    # Build criteria
    criteria = {
        "inactive_days": args.inactive,
        "empty_only": args.empty,
        "pattern": args.pattern,
        "prefix": args.prefix,
        "older_than_days": args.older_than,
    }

    # Filter repositories
    to_archive = filter_repos(repos, criteria)

    if not to_archive:
        print(f"{GREEN}No repositories match the criteria{NC}")
        sys.exit(0)

    # Show what will be archived
    print(f"{BOLD}Repositories to archive: {len(to_archive)}{NC}")
    print()

    now = datetime.now().astimezone()
    for repo in to_archive:
        pushed_at = parse_date(repo.get("pushedAt", ""))
        if pushed_at:
            days_inactive = (now - pushed_at).days
            inactive_str = f"{days_inactive} days inactive"
        else:
            inactive_str = "never pushed"

        empty_str = " [EMPTY]" if repo.get("isEmpty") else ""

        print(f"  {CYAN}{repo['nameWithOwner']}{NC}{empty_str}")
        print(f"    {inactive_str}")

    print()

    if args.dry_run:
        print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
        print(f"Would archive {len(to_archive)} repositories")
        print()
        sys.exit(0)

    # Confirmation
    if not args.yes:
        print(f"{RED}WARNING: This will archive {len(to_archive)} repositories!{NC}")
        response = input("Continue? (yes/N): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
        print()

    # Archive
    print(f"{BOLD}Archiving repositories...{NC}")
    print()

    success = 0
    failed = 0

    for repo in to_archive:
        name = repo["nameWithOwner"]
        print(f"{CYAN}→{NC} {name}...", end=" ")

        if archive_repo(name):
            print(f"{GREEN}✓{NC}")
            success += 1
        else:
            print(f"{RED}✗{NC}")
            failed += 1

    print()
    print(f"{GREEN}✓ {success} repositories archived{NC}")
    if failed:
        print(f"{RED}✗ {failed} repositories failed{NC}")
    print()


if __name__ == "__main__":
    main()
