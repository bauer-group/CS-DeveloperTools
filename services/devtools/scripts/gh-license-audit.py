#!/usr/bin/env python3
# @name: gh-license-audit
# @description: Audit license files across organization repositories
# @category: github
# @usage: gh-license-audit.py [-o <org>] [--missing-only]
"""
gh-license-audit.py - License Audit Tool
Prüft alle Repositories einer Organisation auf Lizenz-Dateien.
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


def get_org_repos(org: str, include_archived: bool = False) -> List[Dict]:
    """Get all repositories for an organization."""
    output = run_gh([
        "api", f"/orgs/{org}/repos",
        "--paginate",
        "-q", ".[] | {name: .name, archived: .archived, visibility: .visibility, license: .license}"
    ])
    if not output:
        return []

    repos = []
    for line in output.strip().split('\n'):
        if line:
            repo = json.loads(line)
            if include_archived or not repo.get("archived", False):
                repos.append(repo)
    return repos


def get_license_file(org: str, repo: str) -> Optional[Dict]:
    """Check for LICENSE file in repository."""
    output = run_gh(["api", f"repos/{org}/{repo}/license"])
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Audit license files across organization repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Audit all repos
  gh-license-audit.py

  # Show only repos without license
  gh-license-audit.py --missing-only

  # Include archived repos
  gh-license-audit.py --include-archived

  # Filter by visibility
  gh-license-audit.py --visibility public

  # Export as JSON
  gh-license-audit.py --json
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only show repos without license"
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived repositories"
    )
    parser.add_argument(
        "--visibility",
        choices=["public", "private", "internal"],
        help="Filter by visibility"
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
        print(f"{BOLD}{CYAN}|                    License Audit Tool                         |{NC}")
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print()

    # Get repositories
    if not args.json:
        print(f"Scanning repositories in {BOLD}{args.org}{NC}...")
    repos = get_org_repos(args.org, args.include_archived)

    if not repos:
        print(f"{RED}[ERROR] No repositories found{NC}")
        sys.exit(1)

    # Filter by visibility
    if args.visibility:
        repos = [r for r in repos if r.get("visibility") == args.visibility]

    if not args.json:
        print(f"  Found {len(repos)} repos")
        print()

    # Analyze licenses
    results = {
        "with_license": [],
        "without_license": [],
        "by_license": {}
    }

    for repo in repos:
        repo_name = repo["name"]
        license_info = repo.get("license")

        if license_info:
            license_name = license_info.get("name", "Unknown")
            license_spdx = license_info.get("spdx_id", "Unknown")

            results["with_license"].append({
                "name": repo_name,
                "license": license_name,
                "spdx_id": license_spdx,
                "visibility": repo.get("visibility")
            })

            if license_name not in results["by_license"]:
                results["by_license"][license_name] = []
            results["by_license"][license_name].append(repo_name)

            if not args.json and not args.missing_only:
                print(f"  {GREEN}✓{NC} {repo_name}: {license_name}")
        else:
            results["without_license"].append({
                "name": repo_name,
                "visibility": repo.get("visibility")
            })

            if not args.json:
                print(f"  {RED}✗{NC} {repo_name}: {RED}No license{NC}")

    # JSON output
    if args.json:
        print(json.dumps({
            "org": args.org,
            "total_repos": len(repos),
            "with_license": len(results["with_license"]),
            "without_license": len(results["without_license"]),
            "repos_without_license": results["without_license"],
            "repos_with_license": results["with_license"],
            "license_distribution": {k: len(v) for k, v in results["by_license"].items()}
        }, indent=2))
        return

    # Summary
    print()
    print("=" * 60)
    print(f"{BOLD}Summary:{NC}")
    print(f"  Total repositories: {len(repos)}")
    print(f"  With license: {GREEN}{len(results['with_license'])}{NC}")
    print(f"  Without license: {RED}{len(results['without_license'])}{NC}")
    print()

    if results["by_license"]:
        print(f"{BOLD}License Distribution:{NC}")
        for license_name, repos_list in sorted(results["by_license"].items(), key=lambda x: -len(x[1])):
            print(f"  {license_name}: {len(repos_list)}")
        print()

    if results["without_license"]:
        coverage = len(results["with_license"]) / len(repos) * 100
        print(f"License coverage: {YELLOW}{coverage:.1f}%{NC}")
        print()
        print(f"{BOLD}Repos needing license:{NC}")
        for repo in results["without_license"][:10]:
            print(f"  - {repo['name']}")
        if len(results["without_license"]) > 10:
            print(f"  ... and {len(results['without_license']) - 10} more")
        print()


if __name__ == "__main__":
    main()
