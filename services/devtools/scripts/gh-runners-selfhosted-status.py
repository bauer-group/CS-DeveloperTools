#!/usr/bin/env python3
# @name: gh-runners-selfhosted-status
# @description: Show self-hosted runner status across organization
# @category: github
# @usage: gh-runners-selfhosted-status.py [-o <org>]
"""
gh-runners-selfhosted-status.py - Self-hosted Runner Status
Zeigt Status aller Self-hosted Runners einer Organisation.
"""

import sys
import json
import subprocess
import argparse
from typing import List, Dict, Optional
from datetime import datetime

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


def get_org_runners(org: str) -> List[Dict]:
    """Get all self-hosted runners for an organization."""
    output = run_gh(["api", f"/orgs/{org}/actions/runners", "--paginate"])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("runners", [])
    except json.JSONDecodeError:
        return []


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


def get_repo_runners(org: str, repo: str) -> List[Dict]:
    """Get self-hosted runners for a specific repository."""
    output = run_gh(["api", f"repos/{org}/{repo}/actions/runners"])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("runners", [])
    except json.JSONDecodeError:
        return []


def get_runner_groups(org: str) -> List[Dict]:
    """Get runner groups for organization."""
    output = run_gh(["api", f"/orgs/{org}/actions/runner-groups"])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("runner_groups", [])
    except json.JSONDecodeError:
        return []


def format_labels(labels: List[Dict]) -> str:
    """Format runner labels."""
    return ", ".join(l.get("name", "") for l in labels if l.get("type") == "custom")


def main():
    parser = argparse.ArgumentParser(
        description="Show self-hosted runner status across organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all organization runners
  gh-runners-selfhosted-status.py

  # Show runners for specific organization
  gh-runners-selfhosted-status.py -o myorg

  # Include per-repository runners
  gh-runners-selfhosted-status.py --include-repo-runners

  # Show runner groups
  gh-runners-selfhosted-status.py --groups

  # Show offline runners only
  gh-runners-selfhosted-status.py --offline-only

  # Export as JSON
  gh-runners-selfhosted-status.py --json
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--include-repo-runners",
        action="store_true",
        help="Include repository-level runners"
    )
    parser.add_argument(
        "--groups",
        action="store_true",
        help="Show runner groups"
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Show only offline runners"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    # Header
    if not args.json:
        print()
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print(f"{BOLD}{CYAN}|              Self-hosted Runner Status                        |{NC}")
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print()

    # Get organization runners
    if not args.json:
        print(f"Fetching runners for {BOLD}{args.org}{NC}...")

    org_runners = get_org_runners(args.org)

    # Get runner groups if requested
    groups = []
    if args.groups:
        groups = get_runner_groups(args.org)

    # Get repo runners if requested
    repo_runners = {}
    if args.include_repo_runners:
        if not args.json:
            print("Scanning repository runners...")
        repos = get_org_repos(args.org)
        for repo in repos:
            runners = get_repo_runners(args.org, repo["name"])
            if runners:
                repo_runners[repo["name"]] = runners

    # Filter offline only
    if args.offline_only:
        org_runners = [r for r in org_runners if r.get("status") == "offline"]
        for repo_name in repo_runners:
            repo_runners[repo_name] = [r for r in repo_runners[repo_name] if r.get("status") == "offline"]

    # JSON output
    if args.json:
        output_data = {
            "org": args.org,
            "organization_runners": org_runners,
            "runner_groups": groups,
            "repository_runners": repo_runners
        }
        print(json.dumps(output_data, indent=2))
        return

    # Display organization runners
    print()
    print(f"{BOLD}Organization Runners:{NC}")
    print()

    if not org_runners:
        print(f"  {DIM}No organization-level runners found{NC}")
    else:
        online = len([r for r in org_runners if r.get("status") == "online"])
        offline = len([r for r in org_runners if r.get("status") == "offline"])
        busy = len([r for r in org_runners if r.get("busy")])

        print(f"  Total: {len(org_runners)} | {GREEN}Online: {online}{NC} | {RED}Offline: {offline}{NC} | {YELLOW}Busy: {busy}{NC}")
        print()

        for runner in org_runners:
            name = runner.get("name", "Unknown")
            status = runner.get("status", "unknown")
            busy_status = runner.get("busy", False)
            os_type = runner.get("os", "unknown")
            labels = format_labels(runner.get("labels", []))

            # Status color
            if status == "online":
                status_str = f"{GREEN}●{NC} online"
                if busy_status:
                    status_str = f"{YELLOW}●{NC} busy"
            else:
                status_str = f"{RED}●{NC} offline"

            print(f"  {BOLD}{name}{NC}")
            print(f"    Status: {status_str}")
            print(f"    OS: {os_type}")
            if labels:
                print(f"    Labels: {CYAN}{labels}{NC}")
            print()

    # Display runner groups
    if args.groups and groups:
        print(f"{BOLD}Runner Groups:{NC}")
        print()

        for group in groups:
            name = group.get("name", "Unknown")
            visibility = group.get("visibility", "unknown")
            default = group.get("default", False)

            print(f"  {BOLD}{name}{NC}")
            print(f"    Visibility: {visibility}")
            if default:
                print(f"    {DIM}(default group){NC}")
            print()

    # Display repository runners
    if args.include_repo_runners:
        print(f"{BOLD}Repository Runners:{NC}")
        print()

        if not repo_runners:
            print(f"  {DIM}No repository-level runners found{NC}")
        else:
            for repo_name, runners in sorted(repo_runners.items()):
                print(f"  {BOLD}{repo_name}:{NC}")
                for runner in runners:
                    name = runner.get("name", "Unknown")
                    status = runner.get("status", "unknown")
                    status_icon = f"{GREEN}●{NC}" if status == "online" else f"{RED}●{NC}"
                    print(f"    {status_icon} {name}")
                print()

    # Summary
    total_runners = len(org_runners)
    for runners in repo_runners.values():
        total_runners += len(runners)

    print("=" * 60)
    print(f"{BOLD}Summary:{NC}")
    print(f"  Total runners: {total_runners}")
    print(f"  Organization runners: {len(org_runners)}")
    if args.include_repo_runners:
        print(f"  Repository runners: {sum(len(r) for r in repo_runners.values())}")
    print()


if __name__ == "__main__":
    main()
