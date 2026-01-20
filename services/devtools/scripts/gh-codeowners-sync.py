#!/usr/bin/env python3
# @name: gh-codeowners-sync
# @description: Sync CODEOWNERS file across organization repositories
# @category: github
# @usage: gh-codeowners-sync.py [-o <org>] --source <repo> [--execute]
"""
gh-codeowners-sync.py - CODEOWNERS Sync Tool
Synchronisiert CODEOWNERS Dateien über alle Repositories einer Organisation.
"""

import sys
import json
import subprocess
import argparse
import base64
from typing import List, Dict, Optional

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Possible CODEOWNERS locations
CODEOWNERS_PATHS = [
    "CODEOWNERS",
    ".github/CODEOWNERS",
    "docs/CODEOWNERS"
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


def get_file_content(org: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
    """Get file content from repository."""
    import urllib.parse
    encoded_path = urllib.parse.quote(path, safe='')

    output = run_gh(["api", f"repos/{org}/{repo}/contents/{encoded_path}?ref={branch}"])
    if not output:
        return None

    try:
        data = json.loads(output)
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")
        return data.get("content")
    except (json.JSONDecodeError, KeyError):
        return None


def get_file_sha(org: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
    """Get SHA of existing file."""
    import urllib.parse
    encoded_path = urllib.parse.quote(path, safe='')

    output = run_gh(["api", f"repos/{org}/{repo}/contents/{encoded_path}?ref={branch}"])
    if not output:
        return None

    try:
        return json.loads(output).get("sha")
    except json.JSONDecodeError:
        return None


def create_or_update_file(org: str, repo: str, path: str, content: str,
                          message: str, branch: str = "main",
                          dry_run: bool = True) -> bool:
    """Create or update a file in repository."""
    if dry_run:
        return True

    import urllib.parse
    encoded_path = urllib.parse.quote(path, safe='')
    encoded_content = base64.b64encode(content.encode()).decode()

    # Check if file exists
    existing_sha = get_file_sha(org, repo, path, branch)

    try:
        args = [
            "api", "-X", "PUT", f"repos/{org}/{repo}/contents/{encoded_path}",
            "-f", f"message={message}",
            "-f", f"content={encoded_content}",
            "-f", f"branch={branch}"
        ]
        if existing_sha:
            args.extend(["-f", f"sha={existing_sha}"])

        run_gh(args)
        return True
    except Exception:
        return False


def find_codeowners(org: str, repo: str, branch: str = "main") -> Optional[Dict]:
    """Find CODEOWNERS file in repository."""
    for path in CODEOWNERS_PATHS:
        content = get_file_content(org, repo, path, branch)
        if content:
            return {"path": path, "content": content}
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Sync CODEOWNERS file across organization repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List CODEOWNERS status across repos
  gh-codeowners-sync.py --list

  # Sync from source repo to all others
  gh-codeowners-sync.py --source template-repo --execute

  # Sync to specific repos only
  gh-codeowners-sync.py --source template-repo --target repo1,repo2 --execute

  # Use specific file path
  gh-codeowners-sync.py --source template-repo --path .github/CODEOWNERS --execute

  # Preview changes
  gh-codeowners-sync.py --source template-repo --diff

  # Export current state
  gh-codeowners-sync.py --export
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--source",
        help="Source repository for CODEOWNERS"
    )
    parser.add_argument(
        "--target",
        help="Comma-separated list of target repos (default: all)"
    )
    parser.add_argument(
        "--path",
        default=".github/CODEOWNERS",
        help="Path for CODEOWNERS file (default: .github/CODEOWNERS)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List CODEOWNERS status across repos"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show differences from source"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export CODEOWNERS status as JSON"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually sync files (default: dry run)"
    )

    args = parser.parse_args()
    dry_run = not args.execute

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    # Header
    if not args.export:
        print()
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print(f"{BOLD}{CYAN}|                  CODEOWNERS Sync Tool                         |{NC}")
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print()

    # Get repositories
    if not args.export:
        print(f"Scanning repositories in {BOLD}{args.org}{NC}...")
    repos = get_org_repos(args.org)

    if not repos:
        print(f"{RED}[ERROR] No repositories found{NC}")
        sys.exit(1)

    if not args.export:
        print(f"  Found {len(repos)} repos")
        print()

    # Collect CODEOWNERS status
    status = []
    for repo in repos:
        repo_name = repo["name"]
        default_branch = repo.get("default_branch", "main")
        codeowners = find_codeowners(args.org, repo_name, default_branch)

        status.append({
            "name": repo_name,
            "branch": default_branch,
            "has_codeowners": codeowners is not None,
            "path": codeowners["path"] if codeowners else None,
            "content": codeowners["content"] if codeowners else None
        })

    # Export mode
    if args.export:
        print(json.dumps(status, indent=2))
        return

    # List mode
    if args.list:
        with_codeowners = [s for s in status if s["has_codeowners"]]
        without_codeowners = [s for s in status if not s["has_codeowners"]]

        print(f"{BOLD}Repositories with CODEOWNERS:{NC}")
        for s in with_codeowners:
            print(f"  {GREEN}✓{NC} {s['name']} ({s['path']})")

        print()
        print(f"{BOLD}Repositories without CODEOWNERS:{NC}")
        for s in without_codeowners:
            print(f"  {RED}✗{NC} {s['name']}")

        print()
        print(f"Coverage: {len(with_codeowners)}/{len(status)} ({len(with_codeowners)/len(status)*100:.1f}%)")
        return

    # Sync mode requires source
    if not args.source:
        print(f"{YELLOW}Use --list to see status, or --source to sync{NC}")
        return

    # Get source CODEOWNERS
    source_repo = next((r for r in repos if r["name"] == args.source), None)
    if not source_repo:
        print(f"{RED}[ERROR] Source repo not found: {args.source}{NC}")
        sys.exit(1)

    source_codeowners = find_codeowners(args.org, args.source, source_repo.get("default_branch", "main"))
    if not source_codeowners:
        print(f"{RED}[ERROR] No CODEOWNERS found in source repo{NC}")
        sys.exit(1)

    source_content = source_codeowners["content"]
    print(f"Source: {BOLD}{args.source}{NC} ({source_codeowners['path']})")
    print()

    if dry_run:
        print(f"{YELLOW}[DRY RUN MODE]{NC} - No changes will be made")
        print()

    # Determine targets
    if args.target:
        target_names = [t.strip() for t in args.target.split(",")]
        targets = [r for r in repos if r["name"] in target_names]
    else:
        targets = [r for r in repos if r["name"] != args.source]

    # Sync to targets
    synced = 0
    skipped = 0
    failed = 0

    for target in targets:
        target_name = target["name"]
        target_status = next((s for s in status if s["name"] == target_name), None)

        # Check if content is same
        if target_status and target_status["content"] == source_content:
            print(f"  {DIM}{target_name}: already in sync{NC}")
            skipped += 1
            continue

        # Diff mode
        if args.diff and target_status and target_status["content"]:
            print(f"{BOLD}{target_name}:{NC}")
            print(f"  Current: {len(target_status['content'])} bytes")
            print(f"  Source:  {len(source_content)} bytes")
            continue

        # Sync
        success = create_or_update_file(
            args.org, target_name, args.path, source_content,
            "chore: sync CODEOWNERS from template",
            target.get("default_branch", "main"),
            dry_run
        )

        if success:
            action = "would sync" if dry_run else "synced"
            print(f"  {GREEN}✓{NC} {target_name}: {action}")
            synced += 1
        else:
            print(f"  {RED}✗{NC} {target_name}: failed")
            failed += 1

    # Summary
    print()
    print(f"Synced: {GREEN}{synced}{NC}, Skipped: {skipped}, Failed: {RED}{failed}{NC}")

    if dry_run and synced > 0:
        print()
        print(f"Run with {BOLD}--execute{NC} to apply changes.")


if __name__ == "__main__":
    main()
