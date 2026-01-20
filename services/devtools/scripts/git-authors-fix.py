#!/usr/bin/env python3
# @name: git-authors-fix
# @description: Fix author name and email in git history
# @category: git
# @usage: git-authors-fix.py --old-email <email> --new-name <name> --new-email <email>
"""
git-authors-fix.py - Git Author Fixer
Korrigiert Autor-Namen und E-Mail-Adressen in der Git-History.
Nützlich für DSGVO-Compliance, Firmenwechsel oder Korrektur von Tippfehlern.
"""

import sys
import subprocess
import argparse
from typing import List, Dict, Optional
import os

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'


def run_cmd(args: List[str], capture: bool = True, cwd: Optional[str] = None) -> Optional[str]:
    """Run command."""
    try:
        if capture:
            result = subprocess.run(args, capture_output=True, text=True, check=True, cwd=cwd)
            return result.stdout.strip()
        else:
            subprocess.run(args, check=True, cwd=cwd)
            return None
    except subprocess.CalledProcessError as e:
        if capture:
            return None
        raise


def is_git_repo(path: str = ".") -> bool:
    """Check if current directory is a git repo."""
    return os.path.isdir(os.path.join(path, ".git"))


def get_all_authors() -> List[Dict]:
    """Get all unique author combinations in history."""
    output = run_cmd(["git", "log", "--format=%aN|%aE", "--all"])
    if not output:
        return []

    authors = {}
    for line in output.split('\n'):
        if '|' in line:
            name, email = line.split('|', 1)
            key = f"{name}|{email}"
            if key not in authors:
                authors[key] = {"name": name, "email": email, "count": 0}
            authors[key]["count"] += 1

    return sorted(authors.values(), key=lambda x: -x["count"])


def count_commits_by_email(email: str) -> int:
    """Count commits by author email."""
    output = run_cmd(["git", "log", "--oneline", "--author", email, "--all"])
    if not output:
        return 0
    return len(output.split('\n'))


def create_mailmap(mappings: List[Dict]) -> str:
    """Create .mailmap content."""
    lines = []
    for m in mappings:
        # Format: Proper Name <proper@email.com> <old@email.com>
        lines.append(f"{m['new_name']} <{m['new_email']}> <{m['old_email']}>")
    return '\n'.join(lines) + '\n'


def rewrite_history(old_email: str, new_name: str, new_email: str,
                    dry_run: bool = True) -> bool:
    """Rewrite git history with git filter-repo."""
    if dry_run:
        return True

    # Check if git-filter-repo is available
    check = run_cmd(["git", "filter-repo", "--version"])
    if not check:
        print(f"{RED}[ERROR] git-filter-repo not installed{NC}")
        print("Install with: pip install git-filter-repo")
        return False

    # Create mailmap
    mailmap_content = f"{new_name} <{new_email}> <{old_email}>\n"
    mailmap_path = ".mailmap"

    # Write mailmap
    with open(mailmap_path, 'w') as f:
        f.write(mailmap_content)

    try:
        # Run git filter-repo
        subprocess.run([
            "git", "filter-repo",
            "--mailmap", mailmap_path,
            "--force"
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        # Clean up mailmap if it was created
        if os.path.exists(mailmap_path):
            os.remove(mailmap_path)


def main():
    parser = argparse.ArgumentParser(
        description="Fix author name and email in git history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all authors in history
  git-authors-fix.py --list

  # Preview changes for specific email
  git-authors-fix.py --old-email old@email.com --new-name "New Name" --new-email new@email.com

  # Execute rewrite
  git-authors-fix.py --old-email old@email.com --new-name "New Name" --new-email new@email.com --execute

  # Fix multiple authors using mailmap
  git-authors-fix.py --mailmap mappings.txt --execute

  # Generate mailmap file
  git-authors-fix.py --generate-mailmap > .mailmap

WARNING: This rewrites git history! Make sure to:
  1. Backup your repository
  2. Coordinate with team members
  3. Force push after changes
        """
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all authors in history"
    )
    parser.add_argument(
        "--old-email",
        help="Email address to replace"
    )
    parser.add_argument(
        "--old-name",
        help="Name to replace (optional, matches by email)"
    )
    parser.add_argument(
        "--new-name",
        help="New author name"
    )
    parser.add_argument(
        "--new-email",
        help="New author email"
    )
    parser.add_argument(
        "--mailmap",
        help="Use mailmap file for multiple replacements"
    )
    parser.add_argument(
        "--generate-mailmap",
        action="store_true",
        help="Generate a template mailmap file"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually rewrite history (default: dry run)"
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
    print(f"{BOLD}{CYAN}|                    Git Author Fixer                           |{NC}")
    print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
    print()

    # List authors
    if args.list:
        authors = get_all_authors()
        if not authors:
            print(f"{YELLOW}No commits found{NC}")
            return

        print(f"{BOLD}Authors in git history:{NC}")
        print()
        for author in authors:
            print(f"  {author['name']} <{author['email']}>")
            print(f"    {DIM}{author['count']} commits{NC}")
        print()
        return

    # Generate mailmap template
    if args.generate_mailmap:
        authors = get_all_authors()
        print("# Git mailmap file")
        print("# Format: Proper Name <proper@email.com> <old@email.com>")
        print("#")
        for author in authors:
            print(f"# {author['name']} <{author['email']}> <{author['email']}>")
        return

    # Validate arguments for rewrite
    if not args.old_email and not args.mailmap:
        print(f"{YELLOW}Use --list to see authors, or provide --old-email to fix{NC}")
        parser.print_help()
        sys.exit(1)

    if args.old_email and (not args.new_name or not args.new_email):
        print(f"{RED}[ERROR] --new-name and --new-email required with --old-email{NC}")
        sys.exit(1)

    # Warning
    print(f"{YELLOW}⚠ WARNING: This will rewrite git history!{NC}")
    print()

    if dry_run:
        print(f"{YELLOW}[DRY RUN MODE]{NC} - No changes will be made")
        print("Use --execute to actually rewrite history")
        print()

    # Count affected commits
    if args.old_email:
        count = count_commits_by_email(args.old_email)
        print(f"Old email: {BOLD}{args.old_email}{NC}")
        print(f"New name:  {BOLD}{args.new_name}{NC}")
        print(f"New email: {BOLD}{args.new_email}{NC}")
        print(f"Commits affected: {CYAN}{count}{NC}")
        print()

        if count == 0:
            print(f"{YELLOW}No commits found with email: {args.old_email}{NC}")
            return

        if not dry_run:
            # Confirm
            print(f"{RED}This will permanently rewrite {count} commits!{NC}")
            confirm = input("Continue? [y/N]: ")
            if confirm.lower() != 'y':
                print("Aborted.")
                return

            # Execute
            print()
            print("Rewriting history...")
            if rewrite_history(args.old_email, args.new_name, args.new_email, dry_run=False):
                print(f"{GREEN}✓ History rewritten successfully{NC}")
                print()
                print(f"{YELLOW}Remember to force push:{NC}")
                print("  git push --force --all")
                print("  git push --force --tags")
            else:
                print(f"{RED}✗ Failed to rewrite history{NC}")
        else:
            print(f"Would rewrite {count} commits")
            print()
            print(f"Run with {BOLD}--execute{NC} to apply changes.")


if __name__ == "__main__":
    main()
