#!/usr/bin/env python3
# @name: gh-clean-releases
# @description: Clean GitHub releases and tags
# @category: github
# @usage: gh-clean-releases.py [--repo <name>] [--keep-latest <n>]
"""
gh-clean-releases.py - Clean GitHub Releases and Tags
Löscht Releases und/oder Tags aus Repositories (nach Topic, Pattern oder einzeln).
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
              limit: int = 200) -> List[Dict]:
    """Get list of repositories."""
    args = ["repo", "list", org, "--json", "name,nameWithOwner", "--limit", str(limit)]

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


def get_releases(repo: str) -> List[Dict]:
    """Get all releases for a repository."""
    output = run_gh(["release", "list", "-R", repo, "--json", "tagName,name,isDraft,isPrerelease"])
    if not output:
        return []
    return json.loads(output)


def get_tags(repo: str) -> List[str]:
    """Get all tags for a repository."""
    output = run_gh(["api", f"repos/{repo}/tags", "--paginate", "-q", ".[].name"])
    if not output:
        return []
    return output.strip().split("\n") if output.strip() else []


def delete_release(repo: str, tag: str, dry_run: bool = False) -> bool:
    """Delete a release by tag name."""
    if dry_run:
        return True
    try:
        run_gh(["release", "delete", tag, "-R", repo, "--yes"], capture=False)
        return True
    except subprocess.CalledProcessError:
        return False


def delete_tag(repo: str, tag: str, dry_run: bool = False) -> bool:
    """Delete a tag."""
    if dry_run:
        return True
    try:
        run_gh(["api", "-X", "DELETE", f"repos/{repo}/git/refs/tags/{tag}"])
        return True
    except subprocess.CalledProcessError:
        return False


def filter_by_pattern(items: List[str], pattern: Optional[str], exclude: Optional[str]) -> List[str]:
    """Filter items by include/exclude patterns."""
    import fnmatch
    result = items

    if pattern:
        result = [i for i in result if fnmatch.fnmatch(i, pattern)]

    if exclude:
        result = [i for i in result if not fnmatch.fnmatch(i, exclude)]

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Clean GitHub releases and tags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List releases and tags for a repo
  gh-clean-releases.py myorg/myrepo --list

  # Delete all releases and tags (dry run)
  gh-clean-releases.py myorg/myrepo --all --dry-run

  # Delete only releases (keep tags)
  gh-clean-releases.py myorg/myrepo --releases-only

  # Delete only tags (keep releases)
  gh-clean-releases.py myorg/myrepo --tags-only

  # Delete pre-releases only
  gh-clean-releases.py myorg/myrepo --prereleases

  # Delete by tag pattern
  gh-clean-releases.py myorg/myrepo --tag-pattern "v0.*"

  # Keep latest N releases
  gh-clean-releases.py myorg/myrepo --keep-latest 5

  # Clean all repos with specific topic
  gh-clean-releases.py -o myorg --topic old-project --all

  # Exclude certain tags
  gh-clean-releases.py myorg/myrepo --all --exclude "v1.0.0"
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
        help="Filter repos by name pattern"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List releases and tags without deleting"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all releases and tags"
    )
    parser.add_argument(
        "--releases-only",
        action="store_true",
        help="Delete only releases (keep tags)"
    )
    parser.add_argument(
        "--tags-only",
        action="store_true",
        help="Delete only tags (keep releases)"
    )
    parser.add_argument(
        "--prereleases",
        action="store_true",
        help="Delete only pre-releases"
    )
    parser.add_argument(
        "--drafts",
        action="store_true",
        help="Delete only draft releases"
    )
    parser.add_argument(
        "--tag-pattern",
        help="Delete only tags matching pattern (e.g., 'v0.*')"
    )
    parser.add_argument(
        "--exclude",
        help="Exclude tags matching pattern from deletion"
    )
    parser.add_argument(
        "--keep-latest",
        type=int,
        metavar="N",
        help="Keep the N most recent releases/tags"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes"
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

    if not args.list and not any([args.all, args.releases_only, args.tags_only,
                                   args.prereleases, args.drafts, args.tag_pattern]):
        print(f"{RED}[ERROR] Specify what to delete: --all, --releases-only, --tags-only, etc.{NC}")
        sys.exit(1)

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                GitHub Release/Tag Cleaner                     ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    # Get target repositories
    repos = []
    if args.repo:
        repos = [{"nameWithOwner": args.repo, "name": args.repo.split("/")[-1]}]
    else:
        print(f"Fetching repositories from {args.org}...")
        repos = get_repos(args.org, topic=args.topic, pattern=args.pattern, limit=args.limit)
        print(f"Found {len(repos)} repositories")
        print()

    if not repos:
        print(f"{YELLOW}No repositories found{NC}")
        sys.exit(0)

    # Process each repository
    total_releases_deleted = 0
    total_tags_deleted = 0

    for repo in repos:
        repo_name = repo["nameWithOwner"]

        releases = get_releases(repo_name)
        tags = get_tags(repo_name)

        if args.list:
            print(f"{BOLD}{repo_name}{NC}")
            print(f"  Releases: {len(releases)}")
            for rel in releases[:10]:
                status = ""
                if rel.get("isDraft"):
                    status = f" {YELLOW}[draft]{NC}"
                elif rel.get("isPrerelease"):
                    status = f" {YELLOW}[prerelease]{NC}"
                print(f"    - {rel['tagName']}: {rel.get('name', '')}{status}")
            if len(releases) > 10:
                print(f"    ... and {len(releases) - 10} more")

            print(f"  Tags: {len(tags)}")
            for tag in tags[:10]:
                print(f"    - {tag}")
            if len(tags) > 10:
                print(f"    ... and {len(tags) - 10} more")
            print()
            continue

        # Determine what to delete
        releases_to_delete = []
        tags_to_delete = []

        if args.all or args.releases_only:
            releases_to_delete = [r["tagName"] for r in releases]
        elif args.prereleases:
            releases_to_delete = [r["tagName"] for r in releases if r.get("isPrerelease")]
        elif args.drafts:
            releases_to_delete = [r["tagName"] for r in releases if r.get("isDraft")]

        if args.all or args.tags_only:
            tags_to_delete = tags.copy()

        if args.tag_pattern:
            tags_to_delete = filter_by_pattern(tags, args.tag_pattern, args.exclude)
            # Also filter releases by tag pattern
            releases_to_delete = filter_by_pattern([r["tagName"] for r in releases],
                                                    args.tag_pattern, args.exclude)
        elif args.exclude:
            releases_to_delete = filter_by_pattern(releases_to_delete, None, args.exclude)
            tags_to_delete = filter_by_pattern(tags_to_delete, None, args.exclude)

        # Keep latest N
        if args.keep_latest:
            if len(releases_to_delete) > args.keep_latest:
                releases_to_delete = releases_to_delete[args.keep_latest:]
            else:
                releases_to_delete = []

            if len(tags_to_delete) > args.keep_latest:
                tags_to_delete = tags_to_delete[args.keep_latest:]
            else:
                tags_to_delete = []

        # Skip tags that have releases (if not deleting releases)
        if not args.all and not args.releases_only and not args.tag_pattern:
            release_tags = {r["tagName"] for r in releases}
            tags_to_delete = [t for t in tags_to_delete if t not in release_tags]

        if not releases_to_delete and not tags_to_delete:
            print(f"{CYAN}→{NC} {repo_name}: nothing to delete")
            continue

        print(f"{BOLD}{repo_name}{NC}")
        print(f"  Releases to delete: {len(releases_to_delete)}")
        print(f"  Tags to delete: {len(tags_to_delete)}")

        if args.dry_run:
            print(f"  {YELLOW}[DRY RUN]{NC}")
            for rel in releases_to_delete:
                print(f"    Would delete release: {rel}")
            for tag in tags_to_delete:
                print(f"    Would delete tag: {tag}")
            total_releases_deleted += len(releases_to_delete)
            total_tags_deleted += len(tags_to_delete)
            print()
            continue

        # Confirmation for destructive operations
        if not args.yes and len(repos) == 1:
            print()
            response = input(f"Delete {len(releases_to_delete)} releases and {len(tags_to_delete)} tags? (yes/N): ")
            if response.lower() != "yes":
                print("Aborted.")
                sys.exit(0)

        # Delete releases first
        for rel in releases_to_delete:
            if delete_release(repo_name, rel):
                print(f"  {GREEN}✓{NC} Deleted release: {rel}")
                total_releases_deleted += 1
            else:
                print(f"  {RED}✗{NC} Failed to delete release: {rel}")

        # Delete tags
        for tag in tags_to_delete:
            if delete_tag(repo_name, tag):
                print(f"  {GREEN}✓{NC} Deleted tag: {tag}")
                total_tags_deleted += 1
            else:
                print(f"  {RED}✗{NC} Failed to delete tag: {tag}")

        print()

    # Summary
    if not args.list:
        print()
        action = "would be " if args.dry_run else ""
        print(f"{GREEN}✓ {total_releases_deleted} releases {action}deleted{NC}")
        print(f"{GREEN}✓ {total_tags_deleted} tags {action}deleted{NC}")
        print()


if __name__ == "__main__":
    main()
