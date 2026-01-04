#!/usr/bin/env python3
# @name: gh-branch-protection
# @description: Manage branch protection rules
# @category: github
# @usage: gh-branch-protection.py <repo> [--branch <name>] [--rules <json>]
"""
gh-branch-protection.py - Manage Branch Protection Rules
Verwaltet Branch-Protection-Rules für GitHub Repositories.
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

# Preset protection rules
PROTECTION_PRESETS = {
    "minimal": {
        "description": "Basic protection - prevent force push and deletion",
        "rules": {
            "allow_force_pushes": False,
            "allow_deletions": False,
        }
    },
    "standard": {
        "description": "Standard protection - require PR reviews",
        "rules": {
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
            },
            "allow_force_pushes": False,
            "allow_deletions": False,
            "required_linear_history": False,
        }
    },
    "strict": {
        "description": "Strict protection - require reviews + status checks",
        "rules": {
            "required_pull_request_reviews": {
                "required_approving_review_count": 2,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": True,
            },
            "required_status_checks": {
                "strict": True,
                "contexts": []
            },
            "allow_force_pushes": False,
            "allow_deletions": False,
            "required_linear_history": True,
            "enforce_admins": True,
        }
    },
    "release": {
        "description": "Release branch - very strict, no direct commits",
        "rules": {
            "required_pull_request_reviews": {
                "required_approving_review_count": 2,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": True,
                "require_last_push_approval": True,
            },
            "required_status_checks": {
                "strict": True,
                "contexts": []
            },
            "allow_force_pushes": False,
            "allow_deletions": False,
            "required_linear_history": True,
            "enforce_admins": True,
            "required_conversation_resolution": True,
        }
    },
}


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


def get_branches(repo: str) -> List[Dict]:
    """Get all branches in a repository."""
    output = run_gh(["api", f"repos/{repo}/branches", "--paginate"])
    if not output:
        return []
    return json.loads(output)


def get_protection(repo: str, branch: str) -> Optional[Dict]:
    """Get branch protection rules."""
    import urllib.parse
    encoded = urllib.parse.quote(branch, safe="")
    output = run_gh(["api", f"repos/{repo}/branches/{encoded}/protection"])
    if not output:
        return None
    return json.loads(output)


def set_protection(repo: str, branch: str, rules: Dict, dry_run: bool = False) -> bool:
    """Set branch protection rules."""
    if dry_run:
        return True

    import urllib.parse
    encoded = urllib.parse.quote(branch, safe="")

    # Build the protection payload
    payload = {
        "required_status_checks": rules.get("required_status_checks"),
        "enforce_admins": rules.get("enforce_admins", False),
        "required_pull_request_reviews": rules.get("required_pull_request_reviews"),
        "restrictions": rules.get("restrictions"),
        "required_linear_history": rules.get("required_linear_history", False),
        "allow_force_pushes": rules.get("allow_force_pushes", False),
        "allow_deletions": rules.get("allow_deletions", False),
        "required_conversation_resolution": rules.get("required_conversation_resolution", False),
    }

    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        # Use GraphQL for more complex updates, REST for simple ones
        run_gh([
            "api", "-X", "PUT",
            f"repos/{repo}/branches/{encoded}/protection",
            "--input", "-"
        ], capture=False)

        # Actually use the REST API with proper input
        cmd = ["gh", "api", "-X", "PUT", f"repos/{repo}/branches/{encoded}/protection"]

        # Add fields
        if "required_status_checks" in payload and payload["required_status_checks"]:
            cmd.extend(["-F", f"required_status_checks[strict]={str(payload['required_status_checks'].get('strict', False)).lower()}"])
            contexts = payload['required_status_checks'].get('contexts', [])
            if contexts:
                for ctx in contexts:
                    cmd.extend(["-F", f"required_status_checks[contexts][]={ctx}"])
            else:
                cmd.extend(["-F", "required_status_checks[contexts][]="])
        else:
            cmd.extend(["-F", "required_status_checks=null"])

        cmd.extend(["-F", f"enforce_admins={str(payload.get('enforce_admins', False)).lower()}"])

        if "required_pull_request_reviews" in payload and payload["required_pull_request_reviews"]:
            pr_reviews = payload["required_pull_request_reviews"]
            cmd.extend(["-F", f"required_pull_request_reviews[dismiss_stale_reviews]={str(pr_reviews.get('dismiss_stale_reviews', False)).lower()}"])
            cmd.extend(["-F", f"required_pull_request_reviews[require_code_owner_reviews]={str(pr_reviews.get('require_code_owner_reviews', False)).lower()}"])
            cmd.extend(["-F", f"required_pull_request_reviews[required_approving_review_count]={pr_reviews.get('required_approving_review_count', 1)}"])
        else:
            cmd.extend(["-F", "required_pull_request_reviews=null"])

        cmd.extend(["-F", "restrictions=null"])
        cmd.extend(["-F", f"required_linear_history={str(payload.get('required_linear_history', False)).lower()}"])
        cmd.extend(["-F", f"allow_force_pushes={str(payload.get('allow_force_pushes', False)).lower()}"])
        cmd.extend(["-F", f"allow_deletions={str(payload.get('allow_deletions', False)).lower()}"])

        subprocess.run(cmd, capture_output=True, check=True)
        return True

    except subprocess.CalledProcessError:
        return False


def delete_protection(repo: str, branch: str, dry_run: bool = False) -> bool:
    """Delete branch protection rules."""
    if dry_run:
        return True

    import urllib.parse
    encoded = urllib.parse.quote(branch, safe="")

    try:
        run_gh(["api", "-X", "DELETE", f"repos/{repo}/branches/{encoded}/protection"])
        return True
    except subprocess.CalledProcessError:
        return False


def format_protection(protection: Dict) -> List[str]:
    """Format protection rules for display."""
    lines = []

    if protection.get("required_pull_request_reviews"):
        pr = protection["required_pull_request_reviews"]
        lines.append(f"  PR Reviews: {pr.get('required_approving_review_count', 1)} required")
        if pr.get("dismiss_stale_reviews"):
            lines.append("    - Dismiss stale reviews")
        if pr.get("require_code_owner_reviews"):
            lines.append("    - Require code owner reviews")

    if protection.get("required_status_checks"):
        checks = protection["required_status_checks"]
        contexts = checks.get("contexts", [])
        strict = "strict" if checks.get("strict") else "non-strict"
        lines.append(f"  Status Checks ({strict}): {len(contexts)} required")
        for ctx in contexts[:5]:
            lines.append(f"    - {ctx}")
        if len(contexts) > 5:
            lines.append(f"    ... and {len(contexts) - 5} more")

    if protection.get("enforce_admins", {}).get("enabled"):
        lines.append("  Enforce for admins: Yes")

    if protection.get("required_linear_history", {}).get("enabled"):
        lines.append("  Linear history: Required")

    if not protection.get("allow_force_pushes", {}).get("enabled", True):
        lines.append("  Force push: Disabled")

    if not protection.get("allow_deletions", {}).get("enabled", True):
        lines.append("  Deletion: Disabled")

    return lines


def main():
    parser = argparse.ArgumentParser(
        description="Manage branch protection rules for GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show protection status for all branches
  gh-branch-protection.py myorg/repo --list

  # Apply standard protection to main branch
  gh-branch-protection.py myorg/repo main --preset standard

  # Apply strict protection to multiple branches
  gh-branch-protection.py myorg/repo main develop --preset strict

  # Apply to all repos in org
  gh-branch-protection.py --org myorg --branch main --preset standard

  # Export protection rules to JSON
  gh-branch-protection.py myorg/repo main --export > rules.json

  # Import protection rules from JSON
  gh-branch-protection.py myorg/repo main --import rules.json

  # Add required status check
  gh-branch-protection.py myorg/repo main --add-check "CI / Build"

  # Remove protection
  gh-branch-protection.py myorg/repo main --remove

Available presets: minimal, standard, strict, release
        """
    )

    parser.add_argument(
        "repo",
        nargs="?",
        help="Repository (owner/name)"
    )
    parser.add_argument(
        "branches",
        nargs="*",
        help="Branch name(s) to protect"
    )
    parser.add_argument(
        "--org",
        help="Apply to all repos in organization"
    )
    parser.add_argument(
        "--branch",
        help="Branch name when using --org"
    )
    parser.add_argument(
        "--preset",
        choices=list(PROTECTION_PRESETS.keys()),
        help="Use predefined protection rules"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List protection status for all branches"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export protection rules as JSON"
    )
    parser.add_argument(
        "--import",
        dest="import_file",
        help="Import protection rules from JSON file"
    )
    parser.add_argument(
        "--add-check",
        action="append",
        help="Add required status check"
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove branch protection"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be done"
    )

    args = parser.parse_args()

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                  Branch Protection Manager                    ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    # Handle org-wide mode
    repos = []
    if args.org:
        output = run_gh(["repo", "list", args.org, "--json", "nameWithOwner", "--limit", "500"])
        if output:
            repos = [r["nameWithOwner"] for r in json.loads(output)]
        if not args.branch:
            print(f"{RED}[ERROR] --branch required with --org{NC}")
            sys.exit(1)
        branches = [args.branch]
    else:
        if not args.repo:
            print(f"{RED}[ERROR] Repository required{NC}")
            sys.exit(1)
        repos = [args.repo]
        branches = args.branches if args.branches else ["main"]

    # List mode
    if args.list:
        for repo in repos:
            print(f"{BOLD}Repository: {repo}{NC}")
            print()

            all_branches = get_branches(repo)
            for branch in all_branches:
                name = branch["name"]
                protected = branch.get("protected", False)

                if protected:
                    print(f"  {GREEN}●{NC} {name} (protected)")
                    protection = get_protection(repo, name)
                    if protection:
                        for line in format_protection(protection):
                            print(f"  {line}")
                else:
                    print(f"  {YELLOW}○{NC} {name}")

            print()
        sys.exit(0)

    # Export mode
    if args.export:
        if not branches:
            print(f"{RED}[ERROR] Branch required for export{NC}")
            sys.exit(1)

        protection = get_protection(repos[0], branches[0])
        if protection:
            print(json.dumps(protection, indent=2))
        else:
            print(f"{YELLOW}No protection rules found{NC}")
        sys.exit(0)

    # Determine rules to apply
    rules = {}
    if args.import_file:
        try:
            with open(args.import_file) as f:
                rules = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"{RED}[ERROR] Failed to read import file: {e}{NC}")
            sys.exit(1)
    elif args.preset:
        rules = PROTECTION_PRESETS[args.preset]["rules"].copy()
        print(f"{CYAN}Preset:{NC} {args.preset}")
        print(f"{CYAN}Description:{NC} {PROTECTION_PRESETS[args.preset]['description']}")
        print()

    # Add status checks if specified
    if args.add_check:
        if "required_status_checks" not in rules:
            rules["required_status_checks"] = {"strict": True, "contexts": []}
        rules["required_status_checks"]["contexts"].extend(args.add_check)

    if args.dry_run:
        print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
        print()

    # Apply rules
    for repo in repos:
        print(f"{BOLD}→ {repo}{NC}")

        for branch in branches:
            if args.remove:
                # Remove protection
                if delete_protection(repo, branch, args.dry_run):
                    print(f"  {RED}-{NC} Removed protection from {branch}")
                else:
                    print(f"  {RED}✗{NC} Failed to remove protection from {branch}")
            elif rules:
                # Set protection
                if set_protection(repo, branch, rules, args.dry_run):
                    print(f"  {GREEN}✓{NC} Protected {branch}")
                else:
                    print(f"  {RED}✗{NC} Failed to protect {branch}")
            else:
                # Just show current status
                protection = get_protection(repo, branch)
                if protection:
                    print(f"  {GREEN}●{NC} {branch} is protected")
                    for line in format_protection(protection):
                        print(f"  {line}")
                else:
                    print(f"  {YELLOW}○{NC} {branch} is not protected")

        print()

    if args.remove:
        print(f"{GREEN}✓ Protection rules removed{NC}")
    elif rules:
        print(f"{GREEN}✓ Protection rules applied{NC}")
    print()


if __name__ == "__main__":
    main()
