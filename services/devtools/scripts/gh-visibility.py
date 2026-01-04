#!/usr/bin/env python3
# @name: gh-visibility
# @description: Change GitHub repository visibility
# @category: github
# @usage: gh-visibility.py <repo> [--public|--private|--internal]
"""
gh-visibility.py - Change GitHub Repository Visibility
Ändert die Sichtbarkeit von Repositories (public/private/internal).
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


def get_repos(org: str, topic: Optional[str] = None, pattern: Optional[str] = None,
              visibility: Optional[str] = None, limit: int = 200) -> List[Dict]:
    """Get list of repositories."""
    args = ["repo", "list", org, "--json", "name,nameWithOwner,visibility,isPrivate",
            "--limit", str(limit)]

    if visibility:
        args.extend(["--visibility", visibility])

    output = run_gh(args)
    if not output:
        return []

    repos = json.loads(output)

    # Filter by topic if specified
    if topic:
        filtered = []
        for repo in repos:
            topics_output = run_gh(["repo", "view", repo["nameWithOwner"], "--json", "repositoryTopics"])
            if topics_output:
                topics_data = json.loads(topics_output)
                repo_topics = [t["name"] for t in topics_data.get("repositoryTopics", [])]
                if topic in repo_topics:
                    filtered.append(repo)
        repos = filtered

    # Filter by pattern if specified
    if pattern:
        import fnmatch
        repos = [r for r in repos if fnmatch.fnmatch(r["name"], pattern)]

    return repos


def change_visibility(repo: str, visibility: str, dry_run: bool = False) -> bool:
    """Change repository visibility."""
    if dry_run:
        return True

    try:
        if visibility == "public":
            run_gh(["repo", "edit", repo, "--visibility", "public"], capture=False)
        elif visibility == "private":
            run_gh(["repo", "edit", repo, "--visibility", "private"], capture=False)
        elif visibility == "internal":
            run_gh(["repo", "edit", repo, "--visibility", "internal"], capture=False)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Change GitHub repository visibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Visibility Options:
  public      Anyone can see the repository
  private     Only collaborators can see the repository
  internal    Only organization members can see (Enterprise only)

Examples:
  # Make a single repo public
  gh-visibility.py myorg/myrepo --public

  # Make all repos with topic 'open-source' public
  gh-visibility.py -o myorg --topic open-source --public

  # Make all repos matching pattern private
  gh-visibility.py -o myorg --pattern "internal-*" --private

  # Preview changes (dry run)
  gh-visibility.py -o myorg --topic deprecated --private --dry-run

  # List current visibility of repos with topic
  gh-visibility.py -o myorg --topic api --list

  # Make all private repos with topic public (with exclusions)
  gh-visibility.py -o myorg --topic plugins --public --exclude "*secret*,*internal*"

  # Convert from private to public with confirmation
  gh-visibility.py -o myorg --current private --topic legacy --public
        """
    )

    parser.add_argument(
        "repo",
        nargs="?",
        help="Specific repository (owner/name)"
    )
    parser.add_argument(
        "-o", "--org",
        help="Organization name for bulk operations"
    )
    parser.add_argument(
        "--topic",
        help="Filter repos by topic"
    )
    parser.add_argument(
        "--pattern",
        help="Filter repos by name pattern (e.g., 'api-*')"
    )
    parser.add_argument(
        "--exclude",
        help="Exclude repos matching patterns (comma-separated)"
    )
    parser.add_argument(
        "--current",
        choices=["public", "private", "internal"],
        help="Only process repos with this current visibility"
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Make repositories public"
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make repositories private"
    )
    parser.add_argument(
        "--internal",
        action="store_true",
        help="Make repositories internal (Enterprise only)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List repositories and their visibility"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max repos to process (default: 200)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.repo and not args.org:
        print(f"{RED}[ERROR] Specify either a repo or --org{NC}")
        sys.exit(1)

    visibility_flags = [args.public, args.private, args.internal]
    if not args.list and sum(visibility_flags) != 1:
        print(f"{RED}[ERROR] Specify exactly one of: --public, --private, --internal{NC}")
        sys.exit(1)

    target_visibility = "public" if args.public else "private" if args.private else "internal"

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                GitHub Visibility Manager                      ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    # Get target repositories
    repos = []
    if args.repo:
        # Get single repo info
        output = run_gh(["repo", "view", args.repo, "--json", "name,nameWithOwner,visibility,isPrivate"])
        if output:
            repos = [json.loads(output)]
        else:
            print(f"{RED}[ERROR] Repository not found: {args.repo}{NC}")
            sys.exit(1)
    else:
        print(f"Fetching repositories from {args.org}...")
        repos = get_repos(args.org, topic=args.topic, pattern=args.pattern,
                         visibility=args.current, limit=args.limit)
        print(f"Found {len(repos)} repositories")
        print()

    if not repos:
        print(f"{YELLOW}No repositories found{NC}")
        sys.exit(0)

    # Apply exclusion patterns
    if args.exclude:
        import fnmatch
        exclude_patterns = [p.strip() for p in args.exclude.split(",")]
        original_count = len(repos)
        repos = [r for r in repos if not any(fnmatch.fnmatch(r["name"], p) for p in exclude_patterns)]
        if len(repos) < original_count:
            print(f"Excluded {original_count - len(repos)} repos by pattern")
            print()

    # List mode
    if args.list:
        print(f"{BOLD}Repository Visibility:{NC}")
        print()

        public_count = 0
        private_count = 0
        internal_count = 0

        for repo in repos:
            vis = repo.get("visibility", "private" if repo.get("isPrivate") else "public")
            if vis == "public":
                icon = f"{GREEN}●{NC}"
                public_count += 1
            elif vis == "internal":
                icon = f"{YELLOW}●{NC}"
                internal_count += 1
            else:
                icon = f"{RED}●{NC}"
                private_count += 1

            print(f"  {icon} {repo['nameWithOwner']:50} {vis}")

        print()
        print(f"Summary: {GREEN}{public_count} public{NC}, {RED}{private_count} private{NC}, {YELLOW}{internal_count} internal{NC}")
        print()
        sys.exit(0)

    # Filter out repos already at target visibility
    repos_to_change = []
    for repo in repos:
        current = repo.get("visibility", "private" if repo.get("isPrivate") else "public")
        if current != target_visibility:
            repos_to_change.append(repo)

    if not repos_to_change:
        print(f"{GREEN}All repositories are already {target_visibility}{NC}")
        sys.exit(0)

    print(f"{BOLD}Changing {len(repos_to_change)} repositories to {target_visibility}:{NC}")
    print()

    for repo in repos_to_change:
        current = repo.get("visibility", "private" if repo.get("isPrivate") else "public")
        print(f"  {repo['nameWithOwner']}: {current} → {target_visibility}")

    print()

    if args.dry_run:
        print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
        print()
        sys.exit(0)

    # Confirmation for sensitive operations
    if not args.yes:
        if target_visibility == "public":
            print(f"{RED}WARNING: Making repositories public exposes all code and history!{NC}")
        response = input(f"Change {len(repos_to_change)} repos to {target_visibility}? (yes/N): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
        print()

    # Change visibility
    changed = 0
    failed = 0

    for repo in repos_to_change:
        repo_name = repo["nameWithOwner"]
        print(f"{CYAN}→{NC} {repo_name}...", end=" ")

        if change_visibility(repo_name, target_visibility):
            print(f"{GREEN}✓ {target_visibility}{NC}")
            changed += 1
        else:
            print(f"{RED}✗ failed{NC}")
            failed += 1

    # Summary
    print()
    print(f"{GREEN}✓ {changed} repositories changed to {target_visibility}{NC}")
    if failed:
        print(f"{RED}✗ {failed} failed{NC}")
    print()


if __name__ == "__main__":
    main()
