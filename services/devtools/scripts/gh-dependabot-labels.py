#!/usr/bin/env python3
# @name: gh-dependabot-labels
# @description: Sync labels from dependabot.yml across organization repos
# @category: github
# @usage: gh-dependabot-labels.py [-o <org>] [--execute] [--cleanup]
"""
gh-dependabot-labels.py - Dependabot Labels Sync Tool
Scannt alle Repos einer Organisation, liest dependabot.yml und erstellt die definierten Labels.
"""

import sys
import json
import subprocess
import argparse
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Set
import yaml

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Standard-Farbe für Dependabot-Labels
DEPENDABOT_LABEL_COLOR = "0366d6"  # GitHub blue


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
    """Get all repositories for an organization."""
    output = run_gh([
        "api", f"/orgs/{org}/repos",
        "--paginate",
        "-q", ".[] | {name: .name, default_branch: .default_branch, archived: .archived}"
    ])
    if not output:
        return []

    repos = []
    for line in output.strip().split('\n'):
        if line:
            repos.append(json.loads(line))
    return repos


def get_dependabot_config(org: str, repo: str, branch: str) -> Optional[Dict]:
    """Fetch dependabot.yml from repository."""
    # Try both .yml and .yaml extensions
    for ext in ["yml", "yaml"]:
        url = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/.github/dependabot.{ext}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')
                return yaml.safe_load(content)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # Try next extension
            return None
        except Exception:
            return None
    return None


def extract_labels_from_config(config: Dict) -> Set[str]:
    """Extract all labels from dependabot config."""
    labels = set()
    if not config:
        return labels

    updates = config.get("updates", [])
    for update in updates:
        update_labels = update.get("labels", [])
        labels.update(update_labels)

    return labels


def get_repo_labels(org: str, repo: str) -> List[Dict]:
    """Get all labels from a repository."""
    output = run_gh(["api", f"repos/{org}/{repo}/labels", "--paginate"])
    if not output:
        return []
    return json.loads(output)


def create_label(org: str, repo: str, name: str, color: str,
                 description: str = "", dry_run: bool = True) -> bool:
    """Create a label in a repository."""
    if dry_run:
        return True

    try:
        run_gh([
            "api", "-X", "POST", f"repos/{org}/{repo}/labels",
            "-f", f"name={name}",
            "-f", f"color={color}",
            "-f", f"description={description}"
        ])
        return True
    except subprocess.CalledProcessError:
        return False


def delete_label(org: str, repo: str, name: str, dry_run: bool = True) -> bool:
    """Delete a label from a repository."""
    if dry_run:
        return True

    import urllib.parse
    encoded_name = urllib.parse.quote(name, safe="")

    try:
        run_gh(["api", "-X", "DELETE", f"repos/{org}/{repo}/labels/{encoded_name}"])
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync labels from dependabot.yml across organization repos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - show what would be done
  gh-dependabot-labels.py

  # Execute label creation
  gh-dependabot-labels.py --execute

  # Also remove labels no longer in dependabot.yml
  gh-dependabot-labels.py --execute --cleanup

  # Scan specific organization
  gh-dependabot-labels.py -o myorg --execute

  # Scan single repo
  gh-dependabot-labels.py --repo myrepo

  # Custom label color
  gh-dependabot-labels.py --color "5319e7"
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--repo",
        help="Only scan specific repository"
    )
    parser.add_argument(
        "--color",
        default=DEPENDABOT_LABEL_COLOR,
        help=f"Color for new labels (default: {DEPENDABOT_LABEL_COLOR})"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove labels that are no longer in dependabot.yml (only dependabot-managed labels)"
    )
    parser.add_argument(
        "--cleanup-prefix",
        default="dependencies",
        help="Only cleanup labels starting with this prefix (default: dependencies)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create/delete labels (default: dry run)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()
    dry_run = not args.execute

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    # Check for PyYAML
    try:
        import yaml
    except ImportError:
        print(f"{RED}[ERROR] PyYAML not installed{NC}")
        print("Run: pip install pyyaml")
        sys.exit(1)

    # Header
    print()
    print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
    print(f"{BOLD}{CYAN}|              Dependabot Labels Sync Tool                      |{NC}")
    print(f"{BOLD}{CYAN}+---------------------------------------------------------------+{NC}")
    print()

    if dry_run:
        print(f"{YELLOW}[DRY RUN MODE]{NC} - No changes will be made")
        print("Use --execute to actually create/delete labels")
        print()

    # Get repositories
    print(f"Scanning repositories in {BOLD}{args.org}{NC}...")

    if args.repo:
        # Single repo mode
        repo_info = run_gh([
            "api", f"repos/{args.org}/{args.repo}",
            "-q", "{name: .name, default_branch: .default_branch, archived: .archived}"
        ])
        if not repo_info:
            print(f"{RED}[ERROR] Repository not found: {args.org}/{args.repo}{NC}")
            sys.exit(1)
        repos = [json.loads(repo_info)]
    else:
        repos = get_org_repos(args.org)

    if not repos:
        print(f"{RED}[ERROR] No repositories found{NC}")
        sys.exit(1)

    # Filter out archived repos
    active_repos = [r for r in repos if not r.get("archived", False)]

    print(f"  Found {len(repos)} repos ({len(active_repos)} active, {len(repos) - len(active_repos)} archived)")
    print()

    # Statistics
    total_repos = 0
    repos_with_dependabot = 0
    labels_created = 0
    labels_deleted = 0
    labels_exist = 0
    all_dependabot_labels: Dict[str, Set[str]] = {}  # repo -> labels

    # Process each repository
    for repo in active_repos:
        repo_name = repo["name"]
        default_branch = repo.get("default_branch", "main")
        total_repos += 1

        # Get dependabot config
        config = get_dependabot_config(args.org, repo_name, default_branch)

        if not config:
            if args.verbose:
                print(f"{DIM}{repo_name}: no dependabot.yml{NC}")
            continue

        repos_with_dependabot += 1

        # Extract labels from config
        dependabot_labels = extract_labels_from_config(config)
        all_dependabot_labels[repo_name] = dependabot_labels

        if not dependabot_labels:
            if args.verbose:
                print(f"{DIM}{repo_name}: dependabot.yml has no labels defined{NC}")
            continue

        print(f"{BOLD}{repo_name}{NC} {DIM}(dependabot.yml){NC}")
        print(f"  Labels defined: {', '.join(sorted(dependabot_labels))}")

        # Get existing labels
        existing_labels = get_repo_labels(args.org, repo_name)
        existing_names = {l["name"].lower(): l["name"] for l in existing_labels}

        # Create missing labels
        for label in sorted(dependabot_labels):
            if label.lower() in existing_names:
                labels_exist += 1
                if args.verbose:
                    print(f"  {DIM}✓ Exists: {label}{NC}")
            else:
                description = f"Dependabot: {label}"
                if create_label(args.org, repo_name, label, args.color, description, dry_run):
                    print(f"  {GREEN}+ Create: {label}{NC}")
                    labels_created += 1
                else:
                    print(f"  {RED}✗ Failed: {label}{NC}")

        # Cleanup old labels if requested
        if args.cleanup:
            for existing in existing_labels:
                label_name = existing["name"]
                # Only cleanup labels that match the prefix and aren't in dependabot config
                if (label_name.lower().startswith(args.cleanup_prefix.lower()) and
                    label_name.lower() not in {l.lower() for l in dependabot_labels}):
                    if delete_label(args.org, repo_name, label_name, dry_run):
                        print(f"  {RED}- Remove: {label_name}{NC}")
                        labels_deleted += 1
                    else:
                        print(f"  {RED}✗ Failed to remove: {label_name}{NC}")

        print()

    # Summary
    print("=" * 60)
    print(f"{BOLD}Summary:{NC}")
    print(f"  Repos scanned: {total_repos}")
    print(f"  Repos with dependabot.yml: {repos_with_dependabot}")
    print(f"  Labels to create: {GREEN}{labels_created}{NC}")
    print(f"  Labels already exist: {labels_exist}")
    if args.cleanup:
        print(f"  Labels to remove: {RED}{labels_deleted}{NC}")
    print()

    if dry_run and (labels_created > 0 or labels_deleted > 0):
        print(f"Run with {BOLD}--execute{NC} to apply these changes.")
        print()


if __name__ == "__main__":
    main()
