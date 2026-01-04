#!/usr/bin/env python3
# @name: gh-secrets-audit
# @description: Audit GitHub repository secrets
# @category: github
# @usage: gh-secrets-audit.py [--org <name>] [--repos <list>]
"""
gh-secrets-audit.py - Audit GitHub Repository Secrets
Prüft Secrets über Repositories hinweg (ohne Werte anzuzeigen).
"""

import sys
import json
import subprocess
import argparse
from typing import List, Dict, Optional, Set
from collections import defaultdict

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


def get_repos(org: str, limit: int = 500) -> List[Dict]:
    """Get list of repositories."""
    output = run_gh([
        "repo", "list", org,
        "--json", "name,nameWithOwner",
        "--limit", str(limit)
    ])
    if not output:
        return []
    return json.loads(output)


def get_repo_secrets(repo: str) -> List[Dict]:
    """Get repository secrets (names only, not values)."""
    output = run_gh(["api", f"repos/{repo}/actions/secrets"])
    if not output:
        return []

    data = json.loads(output)
    return data.get("secrets", [])


def get_repo_variables(repo: str) -> List[Dict]:
    """Get repository variables."""
    output = run_gh(["api", f"repos/{repo}/actions/variables"])
    if not output:
        return []

    data = json.loads(output)
    return data.get("variables", [])


def get_org_secrets(org: str) -> List[Dict]:
    """Get organization secrets."""
    output = run_gh(["api", f"orgs/{org}/actions/secrets"])
    if not output:
        return []

    data = json.loads(output)
    return data.get("secrets", [])


def get_dependabot_secrets(repo: str) -> List[Dict]:
    """Get Dependabot secrets."""
    output = run_gh(["api", f"repos/{repo}/dependabot/secrets"])
    if not output:
        return []

    data = json.loads(output)
    return data.get("secrets", [])


def get_environments(repo: str) -> List[Dict]:
    """Get repository environments."""
    output = run_gh(["api", f"repos/{repo}/environments"])
    if not output:
        return []

    data = json.loads(output)
    return data.get("environments", [])


def get_environment_secrets(repo: str, env_name: str) -> List[Dict]:
    """Get environment secrets."""
    output = run_gh(["api", f"repos/{repo}/environments/{env_name}/secrets"])
    if not output:
        return []

    data = json.loads(output)
    return data.get("secrets", [])


def main():
    parser = argparse.ArgumentParser(
        description="Audit GitHub repository secrets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Audit all repos in organization
  gh-secrets-audit.py -o myorg

  # Audit specific repo
  gh-secrets-audit.py myorg/myrepo

  # Show repos missing required secrets
  gh-secrets-audit.py -o myorg --required DEPLOY_KEY,API_TOKEN

  # Compare secrets across repos
  gh-secrets-audit.py -o myorg --compare

  # Include Dependabot and environment secrets
  gh-secrets-audit.py -o myorg --all

  # Export as JSON
  gh-secrets-audit.py -o myorg --json > secrets-audit.json
        """
    )

    parser.add_argument(
        "repo",
        nargs="?",
        help="Specific repository (owner/name)"
    )
    parser.add_argument(
        "-o", "--org",
        help="Organization name"
    )
    parser.add_argument(
        "--required",
        help="Comma-separated list of required secrets"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare secrets across repositories"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include Dependabot and environment secrets"
    )
    parser.add_argument(
        "--variables",
        action="store_true",
        help="Include repository variables"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Max repos to audit (default: 500)"
    )

    args = parser.parse_args()

    if not args.repo and not args.org:
        print(f"{RED}[ERROR] Specify either a repo or --org{NC}")
        sys.exit(1)

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    if not args.json_output:
        print()
        print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
        print(f"{BOLD}{CYAN}║                  GitHub Secrets Audit                         ║{NC}")
        print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
        print()

    # Get repositories
    repos = []
    if args.repo:
        repos = [{"nameWithOwner": args.repo, "name": args.repo.split("/")[-1]}]
    else:
        if not args.json_output:
            print(f"Fetching repositories from {args.org}...")
        repos = get_repos(args.org, args.limit)
        if not args.json_output:
            print(f"Found {len(repos)} repositories")
            print()

    if not repos:
        print(f"{YELLOW}No repositories found{NC}")
        sys.exit(0)

    # Get org-level secrets
    org_secrets = []
    if args.org:
        org_secrets = get_org_secrets(args.org)

    # Collect data
    audit_data = {
        "org_secrets": [s["name"] for s in org_secrets],
        "repositories": {}
    }

    required_secrets = set()
    if args.required:
        required_secrets = set(s.strip() for s in args.required.split(","))

    all_secrets: Dict[str, Set[str]] = defaultdict(set)
    repos_by_secret: Dict[str, List[str]] = defaultdict(list)
    missing_required: Dict[str, List[str]] = defaultdict(list)

    for repo in repos:
        repo_name = repo["nameWithOwner"]

        if not args.json_output and not args.compare:
            print(f"{CYAN}→{NC} {repo_name}...")

        repo_data = {
            "secrets": [],
            "variables": [],
            "dependabot_secrets": [],
            "environments": {}
        }

        # Get repo secrets
        secrets = get_repo_secrets(repo_name)
        secret_names = [s["name"] for s in secrets]
        repo_data["secrets"] = secret_names

        for name in secret_names:
            all_secrets[repo_name].add(name)
            repos_by_secret[name].append(repo_name)

        # Check required secrets
        if required_secrets:
            missing = required_secrets - set(secret_names)
            if missing:
                missing_required[repo_name] = list(missing)

        # Get variables
        if args.variables:
            variables = get_repo_variables(repo_name)
            repo_data["variables"] = [v["name"] for v in variables]

        # Get Dependabot secrets
        if args.all:
            dependabot = get_dependabot_secrets(repo_name)
            repo_data["dependabot_secrets"] = [s["name"] for s in dependabot]

            # Get environment secrets
            environments = get_environments(repo_name)
            for env in environments:
                env_name = env["name"]
                env_secrets = get_environment_secrets(repo_name, env_name)
                repo_data["environments"][env_name] = [s["name"] for s in env_secrets]

        audit_data["repositories"][repo_name] = repo_data

    # Output
    if args.json_output:
        print(json.dumps(audit_data, indent=2))
        sys.exit(0)

    # Show org secrets
    if org_secrets:
        print()
        print(f"{BOLD}Organization Secrets ({len(org_secrets)}):{NC}")
        for s in org_secrets:
            print(f"  {GREEN}●{NC} {s['name']}")

    # Compare mode
    if args.compare:
        print()
        print(f"{BOLD}Secret Usage Across Repositories:{NC}")
        print()

        # Sort by usage count
        sorted_secrets = sorted(repos_by_secret.items(), key=lambda x: len(x[1]), reverse=True)

        for secret_name, repos_list in sorted_secrets:
            coverage = len(repos_list) / len(repos) * 100
            if coverage == 100:
                icon = f"{GREEN}●{NC}"
            elif coverage >= 50:
                icon = f"{YELLOW}●{NC}"
            else:
                icon = f"{RED}●{NC}"

            print(f"  {icon} {secret_name}: {len(repos_list)}/{len(repos)} repos ({coverage:.0f}%)")

    # Show missing required secrets
    if required_secrets and missing_required:
        print()
        print(f"{BOLD}{RED}Repositories Missing Required Secrets:{NC}")
        print()

        for repo_name, missing in missing_required.items():
            print(f"  {RED}✗{NC} {repo_name}")
            for secret in missing:
                print(f"      Missing: {secret}")

    # Summary for single repo
    if args.repo and not args.compare:
        repo_name = args.repo
        repo_data = audit_data["repositories"].get(repo_name, {})

        print()
        print(f"{BOLD}Repository: {repo_name}{NC}")
        print()

        print(f"{CYAN}Actions Secrets ({len(repo_data.get('secrets', []))}):{NC}")
        for s in repo_data.get("secrets", []):
            print(f"  {GREEN}●{NC} {s}")

        if args.variables and repo_data.get("variables"):
            print()
            print(f"{CYAN}Variables ({len(repo_data['variables'])}):{NC}")
            for v in repo_data["variables"]:
                print(f"  {CYAN}●{NC} {v}")

        if args.all:
            if repo_data.get("dependabot_secrets"):
                print()
                print(f"{CYAN}Dependabot Secrets ({len(repo_data['dependabot_secrets'])}):{NC}")
                for s in repo_data["dependabot_secrets"]:
                    print(f"  {YELLOW}●{NC} {s}")

            for env_name, env_secrets in repo_data.get("environments", {}).items():
                print()
                print(f"{CYAN}Environment '{env_name}' Secrets ({len(env_secrets)}):{NC}")
                for s in env_secrets:
                    print(f"  {GREEN}●{NC} {s}")

    # Summary
    print()
    total_secrets = sum(len(r.get("secrets", [])) for r in audit_data["repositories"].values())
    print(f"{GREEN}✓ Audited {len(repos)} repositories, found {total_secrets} secrets{NC}")

    if missing_required:
        print(f"{RED}✗ {len(missing_required)} repositories missing required secrets{NC}")

    print()


if __name__ == "__main__":
    main()
