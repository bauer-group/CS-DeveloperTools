#!/usr/bin/env python3
# @name: git-squash-history
# @description: Squash old git history to reduce repository size
# @category: git
# @usage: git-squash-history.py [--before <date>] [--keep-recent <n>]
"""
git-squash-history.py - History Squasher
Komprimiert alte Git-History um die Repository-Größe zu reduzieren.
Behält neuere Commits und squasht ältere zu einem einzelnen Commit.
"""

import sys
import subprocess
import argparse
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'


def run_cmd(args: List[str], capture: bool = True, check: bool = True) -> Optional[str]:
    """Run command."""
    try:
        if capture:
            result = subprocess.run(args, capture_output=True, text=True, check=check)
            return result.stdout.strip()
        else:
            subprocess.run(args, check=check)
            return None
    except subprocess.CalledProcessError as e:
        if capture:
            return None
        raise


def is_git_repo() -> bool:
    """Check if current directory is a git repo."""
    return os.path.isdir(".git")


def get_current_branch() -> Optional[str]:
    """Get current branch name."""
    return run_cmd(["git", "branch", "--show-current"])


def get_commit_count() -> int:
    """Get total number of commits."""
    output = run_cmd(["git", "rev-list", "--count", "HEAD"])
    return int(output) if output else 0


def get_commits_before(date: str) -> List[str]:
    """Get commits before a specific date."""
    output = run_cmd(["git", "log", "--format=%H", f"--before={date}"])
    if not output:
        return []
    return output.split('\n')


def get_commits_since(date: str) -> List[str]:
    """Get commits since a specific date."""
    output = run_cmd(["git", "log", "--format=%H", f"--since={date}"])
    if not output:
        return []
    return output.split('\n')


def get_commit_date(sha: str) -> Optional[str]:
    """Get commit date."""
    return run_cmd(["git", "log", "-1", "--format=%ci", sha])


def get_first_commit() -> Optional[str]:
    """Get first commit SHA."""
    output = run_cmd(["git", "rev-list", "--max-parents=0", "HEAD"])
    if output:
        return output.split('\n')[0]
    return None


def get_repo_size() -> str:
    """Get repository size."""
    output = run_cmd(["git", "count-objects", "-vH"])
    if not output:
        return "unknown"

    for line in output.split('\n'):
        if line.startswith("size-pack:"):
            return line.split(':')[1].strip()
    return "unknown"


def create_orphan_branch(name: str) -> bool:
    """Create orphan branch."""
    try:
        run_cmd(["git", "checkout", "--orphan", name], capture=False)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Squash old git history to reduce repository size",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze history
  git-squash-history.py --analyze

  # Keep last 100 commits, squash rest
  git-squash-history.py --keep-recent 100

  # Keep commits from last year
  git-squash-history.py --keep-since "1 year ago"

  # Keep commits after specific date
  git-squash-history.py --keep-since "2023-01-01"

  # Execute squash
  git-squash-history.py --keep-recent 100 --execute

WARNING: This rewrites git history! Make sure to:
  1. Backup your repository
  2. Coordinate with team members
  3. Force push after changes
        """
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze current history size"
    )
    parser.add_argument(
        "--keep-recent",
        type=int,
        help="Keep this many recent commits"
    )
    parser.add_argument(
        "--keep-since",
        help="Keep commits since date (e.g., '2023-01-01' or '1 year ago')"
    )
    parser.add_argument(
        "--message",
        default="chore: squash historical commits",
        help="Commit message for squashed history"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually squash history (default: dry run)"
    )

    args = parser.parse_args()
    dry_run = not args.execute

    # Check if in git repo
    if not is_git_repo():
        print(f"{RED}[ERROR] Not in a git repository{NC}")
        sys.exit(1)

    # Header
    print()
    print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
    print(f"{BOLD}{CYAN}|                   Git History Squasher                        |{NC}")
    print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
    print()

    current_branch = get_current_branch()
    total_commits = get_commit_count()
    repo_size = get_repo_size()

    print(f"Current branch: {BOLD}{current_branch}{NC}")
    print(f"Total commits: {BOLD}{total_commits}{NC}")
    print(f"Repository size: {BOLD}{repo_size}{NC}")
    print()

    # Analyze mode
    if args.analyze:
        first_commit = get_first_commit()
        if first_commit:
            first_date = get_commit_date(first_commit)
            print(f"First commit: {first_date}")

        # Show commit distribution by year
        output = run_cmd(["git", "log", "--format=%ai"])
        if output:
            years = {}
            for line in output.split('\n'):
                if line:
                    year = line[:4]
                    years[year] = years.get(year, 0) + 1

            print()
            print(f"{BOLD}Commits by year:{NC}")
            for year in sorted(years.keys()):
                bar = "█" * min(years[year] // 10, 50)
                print(f"  {year}: {years[year]:5} {bar}")
        return

    # Validate arguments
    if not args.keep_recent and not args.keep_since:
        print(f"{YELLOW}Specify --keep-recent or --keep-since{NC}")
        print("Use --analyze to see history distribution")
        sys.exit(1)

    # Calculate cutoff
    if args.keep_recent:
        if args.keep_recent >= total_commits:
            print(f"{YELLOW}Keep count ({args.keep_recent}) >= total commits ({total_commits}){NC}")
            print("Nothing to squash.")
            return

        # Get SHA at cutoff point
        output = run_cmd(["git", "log", "--format=%H", f"-{args.keep_recent + 1}"])
        if not output:
            print(f"{RED}[ERROR] Failed to get commit history{NC}")
            sys.exit(1)
        commits = output.split('\n')
        cutoff_sha = commits[-1] if len(commits) > args.keep_recent else None
        commits_to_squash = total_commits - args.keep_recent
    else:
        # Keep since date
        recent_commits = get_commits_since(args.keep_since)
        if not recent_commits:
            print(f"{YELLOW}No commits found since {args.keep_since}{NC}")
            return

        commits_to_squash = total_commits - len(recent_commits)
        if commits_to_squash <= 0:
            print(f"{YELLOW}All commits are after {args.keep_since}{NC}")
            print("Nothing to squash.")
            return

        # Get SHA just before the cutoff
        old_commits = get_commits_before(args.keep_since)
        cutoff_sha = old_commits[0] if old_commits else None

    if not cutoff_sha:
        print(f"{RED}[ERROR] Could not determine cutoff point{NC}")
        sys.exit(1)

    cutoff_date = get_commit_date(cutoff_sha)

    print(f"Commits to squash: {YELLOW}{commits_to_squash}{NC}")
    print(f"Commits to keep: {GREEN}{total_commits - commits_to_squash}{NC}")
    print(f"Cutoff at: {cutoff_sha[:8]} ({cutoff_date})")
    print()

    if dry_run:
        print(f"{YELLOW}[DRY RUN MODE]{NC} - No changes will be made")
        print()
        print(f"This would:")
        print(f"  1. Create new branch with squashed history")
        print(f"  2. Squash {commits_to_squash} old commits into one")
        print(f"  3. Keep {total_commits - commits_to_squash} recent commits")
        print()
        print(f"Run with {BOLD}--execute{NC} to proceed.")
        print()
        print(f"{RED}⚠ WARNING: This will rewrite git history!{NC}")
        print("Make sure to backup and coordinate with your team.")
        return

    # Execute squash
    print(f"{RED}⚠ WARNING: This will permanently rewrite git history!{NC}")
    confirm = input("Continue? [y/N]: ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    print()
    print("Squashing history...")

    # Create backup branch
    backup_branch = f"backup-{current_branch}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    run_cmd(["git", "branch", backup_branch])
    print(f"  Created backup branch: {backup_branch}")

    # Create new orphan branch
    new_branch = f"squashed-{current_branch}"
    if not create_orphan_branch(new_branch):
        print(f"{RED}[ERROR] Failed to create orphan branch{NC}")
        sys.exit(1)

    # Add all files and create initial commit
    run_cmd(["git", "add", "-A"], capture=False)
    run_cmd(["git", "commit", "-m", args.message], capture=False, check=False)

    # Cherry-pick recent commits
    print("  Cherry-picking recent commits...")
    recent_commits_output = run_cmd(["git", "log", "--format=%H", "--reverse", f"{cutoff_sha}..{current_branch}"])
    if recent_commits_output:
        for sha in recent_commits_output.split('\n'):
            if sha:
                result = run_cmd(["git", "cherry-pick", sha], check=False)
                if result is None:
                    # Cherry-pick might fail, try to continue
                    run_cmd(["git", "cherry-pick", "--abort"], check=False)
                    print(f"    {YELLOW}Skipped: {sha[:8]}{NC}")

    print()
    print(f"{GREEN}✓ History squashed successfully{NC}")
    print()
    print(f"New branch: {BOLD}{new_branch}{NC}")
    print(f"Backup: {BOLD}{backup_branch}{NC}")
    print()
    print("To complete:")
    print(f"  1. Review the new branch: git log {new_branch}")
    print(f"  2. Replace main branch: git branch -D {current_branch} && git branch -m {new_branch} {current_branch}")
    print(f"  3. Force push: git push --force")
    print()


if __name__ == "__main__":
    main()
