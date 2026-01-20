#!/usr/bin/env python3
# @name: gh-webhook-manager
# @description: Manage webhooks across organization repositories
# @category: github
# @usage: gh-webhook-manager.py [-o <org>] [--list|--add|--delete] [--execute]
"""
gh-webhook-manager.py - Webhook Manager
Verwaltet Webhooks über alle Repositories einer Organisation.
"""

import sys
import json
import subprocess
import argparse
from typing import List, Dict, Optional
import urllib.parse

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'


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
        "-q", ".[] | select(.archived == false) | {name: .name}"
    ])
    if not output:
        return []

    repos = []
    for line in output.strip().split('\n'):
        if line:
            repos.append(json.loads(line))
    return repos


def get_repo_webhooks(org: str, repo: str) -> List[Dict]:
    """Get webhooks for a repository."""
    output = run_gh(["api", f"repos/{org}/{repo}/hooks"])
    if not output:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def create_webhook(org: str, repo: str, url: str, events: List[str],
                   content_type: str = "json", secret: Optional[str] = None,
                   active: bool = True, dry_run: bool = True) -> bool:
    """Create a webhook in a repository."""
    if dry_run:
        return True

    config = {
        "url": url,
        "content_type": content_type,
    }
    if secret:
        config["secret"] = secret

    data = {
        "name": "web",
        "active": active,
        "events": events,
        "config": config
    }

    try:
        run_gh([
            "api", "-X", "POST", f"repos/{org}/{repo}/hooks",
            "--input", "-"
        ])
        return True
    except Exception:
        return False


def delete_webhook(org: str, repo: str, hook_id: int, dry_run: bool = True) -> bool:
    """Delete a webhook from a repository."""
    if dry_run:
        return True

    try:
        run_gh(["api", "-X", "DELETE", f"repos/{org}/{repo}/hooks/{hook_id}"])
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manage webhooks across organization repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all webhooks across repos
  gh-webhook-manager.py --list

  # List webhooks for specific repo
  gh-webhook-manager.py --repo myrepo --list

  # Find repos with webhook URL
  gh-webhook-manager.py --find-url "https://example.com/webhook"

  # Add webhook to all repos
  gh-webhook-manager.py --add --url "https://example.com/hook" --events push --execute

  # Add webhook with secret
  gh-webhook-manager.py --add --url "https://example.com/hook" --events push,pull_request --secret "mysecret" --execute

  # Delete webhook by URL pattern
  gh-webhook-manager.py --delete --url-pattern "old-service.com" --execute

  # Export webhooks to JSON
  gh-webhook-manager.py --export > webhooks.json
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--repo",
        help="Only process specific repository"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all webhooks"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export webhooks as JSON"
    )
    parser.add_argument(
        "--find-url",
        help="Find webhooks with specific URL"
    )
    parser.add_argument(
        "--add",
        action="store_true",
        help="Add webhook to repos"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete webhooks"
    )
    parser.add_argument(
        "--url",
        help="Webhook URL (for --add)"
    )
    parser.add_argument(
        "--url-pattern",
        help="URL pattern to match (for --delete)"
    )
    parser.add_argument(
        "--events",
        default="push",
        help="Comma-separated events (default: push)"
    )
    parser.add_argument(
        "--secret",
        help="Webhook secret"
    )
    parser.add_argument(
        "--content-type",
        default="json",
        choices=["json", "form"],
        help="Content type (default: json)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually apply changes (default: dry run)"
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
        print(f"{BOLD}{CYAN}|                    Webhook Manager                            |{NC}")
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print()

    # Get repositories
    if args.repo:
        repos = [{"name": args.repo}]
    else:
        if not args.export:
            print(f"Scanning repositories in {BOLD}{args.org}{NC}...")
        repos = get_org_repos(args.org)

    if not repos:
        print(f"{RED}[ERROR] No repositories found{NC}")
        sys.exit(1)

    if not args.export:
        print(f"  Found {len(repos)} repos")
        print()

    # Collect all webhooks
    all_webhooks = []
    for repo in repos:
        repo_name = repo["name"]
        hooks = get_repo_webhooks(args.org, repo_name)
        for hook in hooks:
            hook["_repo"] = repo_name
            all_webhooks.append(hook)

    # Export mode
    if args.export:
        export_data = []
        for hook in all_webhooks:
            export_data.append({
                "repo": hook["_repo"],
                "id": hook["id"],
                "url": hook.get("config", {}).get("url", ""),
                "events": hook.get("events", []),
                "active": hook.get("active", False)
            })
        print(json.dumps(export_data, indent=2))
        return

    # List mode
    if args.list or args.find_url:
        search_url = args.find_url.lower() if args.find_url else None

        print(f"{BOLD}Webhooks:{NC}")
        print()

        repos_with_hooks = {}
        for hook in all_webhooks:
            url = hook.get("config", {}).get("url", "")

            if search_url and search_url not in url.lower():
                continue

            repo_name = hook["_repo"]
            if repo_name not in repos_with_hooks:
                repos_with_hooks[repo_name] = []
            repos_with_hooks[repo_name].append(hook)

        if not repos_with_hooks:
            if search_url:
                print(f"{DIM}No webhooks found matching '{args.find_url}'{NC}")
            else:
                print(f"{DIM}No webhooks found{NC}")
            return

        for repo_name, hooks in sorted(repos_with_hooks.items()):
            print(f"{BOLD}{repo_name}{NC}")
            for hook in hooks:
                url = hook.get("config", {}).get("url", "N/A")
                events = ", ".join(hook.get("events", []))
                active = hook.get("active", False)
                status = f"{GREEN}active{NC}" if active else f"{RED}inactive{NC}"
                print(f"  [{hook['id']}] {url}")
                print(f"      Events: {events}")
                print(f"      Status: {status}")
            print()

        print(f"Total: {len(all_webhooks)} webhooks in {len(repos_with_hooks)} repos")
        return

    # Add mode
    if args.add:
        if not args.url:
            print(f"{RED}[ERROR] --url required for --add{NC}")
            sys.exit(1)

        if dry_run:
            print(f"{YELLOW}[DRY RUN MODE]{NC} - No changes will be made")
            print()

        events = [e.strip() for e in args.events.split(",")]
        print(f"Adding webhook to {len(repos)} repos:")
        print(f"  URL: {args.url}")
        print(f"  Events: {', '.join(events)}")
        print()

        added = 0
        skipped = 0
        failed = 0

        for repo in repos:
            repo_name = repo["name"]

            # Check if webhook already exists
            existing = get_repo_webhooks(args.org, repo_name)
            existing_urls = [h.get("config", {}).get("url", "") for h in existing]

            if args.url in existing_urls:
                print(f"  {DIM}{repo_name}: already exists{NC}")
                skipped += 1
                continue

            # Create webhook
            success = create_webhook(
                args.org, repo_name, args.url, events,
                content_type=args.content_type,
                secret=args.secret,
                dry_run=dry_run
            )

            if success:
                print(f"  {GREEN}+ {repo_name}{NC}")
                added += 1
            else:
                print(f"  {RED}✗ {repo_name}{NC}")
                failed += 1

        print()
        print(f"Added: {GREEN}{added}{NC}, Skipped: {skipped}, Failed: {RED}{failed}{NC}")

        if dry_run:
            print()
            print(f"Run with {BOLD}--execute{NC} to apply changes.")
        return

    # Delete mode
    if args.delete:
        if not args.url_pattern:
            print(f"{RED}[ERROR] --url-pattern required for --delete{NC}")
            sys.exit(1)

        if dry_run:
            print(f"{YELLOW}[DRY RUN MODE]{NC} - No changes will be made")
            print()

        pattern = args.url_pattern.lower()
        print(f"Deleting webhooks matching: {pattern}")
        print()

        deleted = 0
        failed = 0

        for hook in all_webhooks:
            url = hook.get("config", {}).get("url", "")
            if pattern not in url.lower():
                continue

            repo_name = hook["_repo"]
            hook_id = hook["id"]

            if delete_webhook(args.org, repo_name, hook_id, dry_run):
                print(f"  {RED}- {repo_name}: {url}{NC}")
                deleted += 1
            else:
                print(f"  {RED}✗ {repo_name}: Failed{NC}")
                failed += 1

        print()
        print(f"Deleted: {RED}{deleted}{NC}, Failed: {failed}")

        if dry_run and deleted > 0:
            print()
            print(f"Run with {BOLD}--execute{NC} to apply changes.")
        return

    # Default: show summary
    print(f"Total webhooks: {len(all_webhooks)}")
    print()
    print("Use --list to see details, --add to create, --delete to remove")


if __name__ == "__main__":
    main()
