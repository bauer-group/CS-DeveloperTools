#!/usr/bin/env python3
# @name: gh-environments-audit
# @description: Audit deployment environments across organization repositories
# @category: github
# @usage: gh-environments-audit.py [-o <org>]
"""
gh-environments-audit.py - Environments Audit Tool
Prüft Deployment Environments und deren Konfiguration über alle Repositories.
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


def get_environments(org: str, repo: str) -> List[Dict]:
    """Get environments for a repository."""
    output = run_gh(["api", f"repos/{org}/{repo}/environments"])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("environments", [])
    except json.JSONDecodeError:
        return []


def get_environment_secrets(org: str, repo: str, env_name: str) -> List[Dict]:
    """Get secrets for an environment."""
    import urllib.parse
    encoded_env = urllib.parse.quote(env_name, safe='')
    output = run_gh(["api", f"repos/{org}/{repo}/environments/{encoded_env}/secrets"])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("secrets", [])
    except json.JSONDecodeError:
        return []


def get_environment_variables(org: str, repo: str, env_name: str) -> List[Dict]:
    """Get variables for an environment."""
    import urllib.parse
    encoded_env = urllib.parse.quote(env_name, safe='')
    output = run_gh(["api", f"repos/{org}/{repo}/environments/{encoded_env}/variables"])
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("variables", [])
    except json.JSONDecodeError:
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Audit deployment environments across organization repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Audit all environments
  gh-environments-audit.py

  # Audit specific organization
  gh-environments-audit.py -o myorg

  # Show only repos with environments
  gh-environments-audit.py --with-envs-only

  # Show environment secrets/variables
  gh-environments-audit.py --show-secrets

  # Check for missing protection rules
  gh-environments-audit.py --check-protection

  # Export as JSON
  gh-environments-audit.py --json
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--repo",
        help="Audit specific repository"
    )
    parser.add_argument(
        "--with-envs-only",
        action="store_true",
        help="Show only repos with environments"
    )
    parser.add_argument(
        "--show-secrets",
        action="store_true",
        help="Show environment secrets and variables"
    )
    parser.add_argument(
        "--check-protection",
        action="store_true",
        help="Check for environments without protection rules"
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
        print(f"{BOLD}{CYAN}|              Deployment Environments Audit                    |{NC}")
        print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
        print()

    # Get repositories
    if args.repo:
        repos = [{"name": args.repo}]
    else:
        if not args.json:
            print(f"Scanning repositories in {BOLD}{args.org}{NC}...")
        repos = get_org_repos(args.org)

    if not repos:
        print(f"{RED}[ERROR] No repositories found{NC}")
        sys.exit(1)

    if not args.json:
        print(f"  Found {len(repos)} repos")
        print()

    # Collect environment data
    all_envs = []
    repos_with_envs = 0
    unprotected_envs = []

    for repo in repos:
        repo_name = repo["name"]
        environments = get_environments(args.org, repo_name)

        if not environments:
            if not args.with_envs_only and not args.json:
                pass  # Skip repos without envs in normal output
            continue

        repos_with_envs += 1
        repo_data = {
            "repo": repo_name,
            "environments": []
        }

        if not args.json:
            print(f"{BOLD}{repo_name}{NC}")

        for env in environments:
            env_name = env.get("name", "Unknown")
            env_data = {
                "name": env_name,
                "protection_rules": env.get("protection_rules", []),
                "deployment_branch_policy": env.get("deployment_branch_policy"),
            }

            # Check protection
            has_protection = bool(env.get("protection_rules")) or bool(env.get("deployment_branch_policy"))

            if args.show_secrets:
                secrets = get_environment_secrets(args.org, repo_name, env_name)
                variables = get_environment_variables(args.org, repo_name, env_name)
                env_data["secrets"] = [s.get("name") for s in secrets]
                env_data["variables"] = [v.get("name") for v in variables]

            repo_data["environments"].append(env_data)

            # Track unprotected
            if not has_protection:
                unprotected_envs.append({"repo": repo_name, "env": env_name})

            # Display
            if not args.json:
                protection_icon = f"{GREEN}✓{NC}" if has_protection else f"{RED}✗{NC}"
                print(f"  {CYAN}→{NC} {env_name} [{protection_icon} protected]")

                # Show protection rules
                for rule in env.get("protection_rules", []):
                    rule_type = rule.get("type", "unknown")
                    if rule_type == "required_reviewers":
                        reviewers = rule.get("reviewers", [])
                        reviewer_names = [r.get("reviewer", {}).get("login", "?") for r in reviewers]
                        print(f"      Reviewers: {', '.join(reviewer_names)}")
                    elif rule_type == "wait_timer":
                        wait = rule.get("wait_timer", 0)
                        print(f"      Wait timer: {wait} minutes")
                    elif rule_type == "branch_policy":
                        print(f"      Branch policy enabled")

                # Show branch policy
                branch_policy = env.get("deployment_branch_policy")
                if branch_policy:
                    if branch_policy.get("protected_branches"):
                        print(f"      Deploy: protected branches only")
                    elif branch_policy.get("custom_branch_policies"):
                        print(f"      Deploy: custom branch rules")

                # Show secrets/variables
                if args.show_secrets:
                    if env_data.get("secrets"):
                        print(f"      Secrets: {', '.join(env_data['secrets'])}")
                    if env_data.get("variables"):
                        print(f"      Variables: {', '.join(env_data['variables'])}")

        all_envs.append(repo_data)

        if not args.json:
            print()

    # JSON output
    if args.json:
        print(json.dumps({
            "org": args.org,
            "repos_scanned": len(repos),
            "repos_with_environments": repos_with_envs,
            "unprotected_environments": unprotected_envs,
            "data": all_envs
        }, indent=2))
        return

    # Summary
    total_envs = sum(len(r["environments"]) for r in all_envs)

    print("=" * 60)
    print(f"{BOLD}Summary:{NC}")
    print(f"  Repos scanned: {len(repos)}")
    print(f"  Repos with environments: {repos_with_envs}")
    print(f"  Total environments: {total_envs}")
    print()

    # Environment distribution
    if all_envs:
        env_names = {}
        for repo_data in all_envs:
            for env in repo_data["environments"]:
                name = env["name"]
                env_names[name] = env_names.get(name, 0) + 1

        print(f"{BOLD}Environment Distribution:{NC}")
        for name, count in sorted(env_names.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count} repos")
        print()

    # Check protection warnings
    if args.check_protection and unprotected_envs:
        print(f"{YELLOW}⚠ Environments without protection:{NC}")
        for item in unprotected_envs:
            print(f"  {item['repo']}/{item['env']}")
        print()
        print(f"Consider adding reviewers or branch policies for production environments.")
        print()


if __name__ == "__main__":
    main()
