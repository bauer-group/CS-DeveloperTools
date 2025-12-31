#!/usr/bin/env python3
"""
gh-labels-sync.py - Sync Labels Between Repositories
Synchronisiert Labels zwischen GitHub Repositories.
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

# Standard label sets
STANDARD_LABELS = {
    "minimal": [
        {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
        {"name": "enhancement", "color": "a2eeef", "description": "New feature or request"},
        {"name": "documentation", "color": "0075ca", "description": "Improvements or additions to documentation"},
    ],
    "standard": [
        {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
        {"name": "enhancement", "color": "a2eeef", "description": "New feature or request"},
        {"name": "documentation", "color": "0075ca", "description": "Improvements or additions to documentation"},
        {"name": "good first issue", "color": "7057ff", "description": "Good for newcomers"},
        {"name": "help wanted", "color": "008672", "description": "Extra attention is needed"},
        {"name": "question", "color": "d876e3", "description": "Further information is requested"},
        {"name": "wontfix", "color": "ffffff", "description": "This will not be worked on"},
        {"name": "duplicate", "color": "cfd3d7", "description": "This issue or pull request already exists"},
        {"name": "invalid", "color": "e4e669", "description": "This doesn't seem right"},
    ],
    "priority": [
        {"name": "priority: critical", "color": "b60205", "description": "Critical priority"},
        {"name": "priority: high", "color": "d93f0b", "description": "High priority"},
        {"name": "priority: medium", "color": "fbca04", "description": "Medium priority"},
        {"name": "priority: low", "color": "0e8a16", "description": "Low priority"},
    ],
    "type": [
        {"name": "type: bug", "color": "d73a4a", "description": "Bug report"},
        {"name": "type: feature", "color": "a2eeef", "description": "Feature request"},
        {"name": "type: maintenance", "color": "fef2c0", "description": "Maintenance task"},
        {"name": "type: security", "color": "ee0701", "description": "Security issue"},
        {"name": "type: performance", "color": "5319e7", "description": "Performance improvement"},
    ],
    "status": [
        {"name": "status: blocked", "color": "b60205", "description": "Blocked by another issue"},
        {"name": "status: in progress", "color": "0052cc", "description": "Work in progress"},
        {"name": "status: review needed", "color": "fbca04", "description": "Needs review"},
        {"name": "status: ready", "color": "0e8a16", "description": "Ready for implementation"},
    ],
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


def get_labels(repo: str) -> List[Dict]:
    """Get all labels from a repository."""
    output = run_gh(["api", f"repos/{repo}/labels", "--paginate"])
    if not output:
        return []
    return json.loads(output)


def create_label(repo: str, name: str, color: str, description: str = "", dry_run: bool = False) -> bool:
    """Create a label in a repository."""
    if dry_run:
        return True

    data = {
        "name": name,
        "color": color.lstrip("#"),
        "description": description[:100] if description else ""
    }

    try:
        run_gh([
            "api", "-X", "POST", f"repos/{repo}/labels",
            "-f", f"name={data['name']}",
            "-f", f"color={data['color']}",
            "-f", f"description={data['description']}"
        ])
        return True
    except subprocess.CalledProcessError:
        return False


def update_label(repo: str, name: str, color: str, description: str = "", new_name: str = "", dry_run: bool = False) -> bool:
    """Update an existing label."""
    if dry_run:
        return True

    import urllib.parse
    encoded_name = urllib.parse.quote(name, safe="")

    args = [
        "api", "-X", "PATCH", f"repos/{repo}/labels/{encoded_name}",
        "-f", f"color={color.lstrip('#')}"
    ]

    if description:
        args.extend(["-f", f"description={description[:100]}"])
    if new_name and new_name != name:
        args.extend(["-f", f"new_name={new_name}"])

    try:
        run_gh(args)
        return True
    except subprocess.CalledProcessError:
        return False


def delete_label(repo: str, name: str, dry_run: bool = False) -> bool:
    """Delete a label from a repository."""
    if dry_run:
        return True

    import urllib.parse
    encoded_name = urllib.parse.quote(name, safe="")

    try:
        run_gh(["api", "-X", "DELETE", f"repos/{repo}/labels/{encoded_name}"])
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync labels between GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Copy labels from source to target repo
  gh-labels-sync.py source/repo target/repo

  # Sync labels to multiple repos
  gh-labels-sync.py source/repo target1/repo target2/repo

  # Apply standard label set to repo
  gh-labels-sync.py --preset standard myorg/repo

  # Apply multiple presets
  gh-labels-sync.py --preset standard --preset priority myorg/repo

  # Export labels to JSON
  gh-labels-sync.py source/repo --export > labels.json

  # Import labels from JSON
  gh-labels-sync.py target/repo --import labels.json

  # Sync and remove labels not in source
  gh-labels-sync.py source/repo target/repo --delete-extra

  # Dry run
  gh-labels-sync.py source/repo target/repo --dry-run

Available presets: minimal, standard, priority, type, status
        """
    )

    parser.add_argument(
        "repos",
        nargs="*",
        help="Source repo followed by target repo(s), or just target repo(s) with --preset"
    )
    parser.add_argument(
        "--preset",
        action="append",
        choices=list(STANDARD_LABELS.keys()),
        help="Use predefined label set"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export labels as JSON"
    )
    parser.add_argument(
        "--import",
        dest="import_file",
        help="Import labels from JSON file"
    )
    parser.add_argument(
        "--delete-extra",
        action="store_true",
        help="Delete labels not in source"
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update color/description of existing labels"
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

    # Determine source labels
    source_labels = []

    if args.import_file:
        # Import from file
        try:
            with open(args.import_file) as f:
                source_labels = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"{RED}[ERROR] Failed to read import file: {e}{NC}")
            sys.exit(1)
        target_repos = args.repos
        source_name = args.import_file

    elif args.preset:
        # Use preset(s)
        for preset in args.preset:
            source_labels.extend(STANDARD_LABELS[preset])
        target_repos = args.repos
        source_name = f"presets: {', '.join(args.preset)}"

    else:
        # Source repo
        if len(args.repos) < 2 and not args.export:
            print(f"{RED}[ERROR] Specify source and target repos, or use --preset/--import{NC}")
            sys.exit(1)

        if args.export:
            if not args.repos:
                print(f"{RED}[ERROR] Specify repo to export{NC}")
                sys.exit(1)
            source_repo = args.repos[0]
            labels = get_labels(source_repo)
            export_data = [
                {"name": l["name"], "color": l["color"], "description": l.get("description", "")}
                for l in labels
            ]
            print(json.dumps(export_data, indent=2))
            sys.exit(0)

        source_repo = args.repos[0]
        source_labels = get_labels(source_repo)
        target_repos = args.repos[1:]
        source_name = source_repo

    if not target_repos:
        print(f"{RED}[ERROR] No target repositories specified{NC}")
        sys.exit(1)

    if not source_labels:
        print(f"{YELLOW}No source labels found{NC}")
        sys.exit(0)

    # Console output
    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                    GitHub Labels Sync                         ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    print(f"{CYAN}Source:{NC} {source_name}")
    print(f"{CYAN}Labels:{NC} {len(source_labels)}")
    print(f"{CYAN}Targets:{NC} {', '.join(target_repos)}")
    print()

    if args.dry_run:
        print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
        print()

    # Create lookup for source labels
    source_by_name = {l["name"].lower(): l for l in source_labels}

    # Process each target repo
    for target in target_repos:
        print(f"{BOLD}→ {target}{NC}")

        # Get existing labels
        existing = get_labels(target)
        existing_by_name = {l["name"].lower(): l for l in existing}

        created = 0
        updated = 0
        deleted = 0
        skipped = 0

        # Create/update labels
        for label in source_labels:
            name = label["name"]
            color = label.get("color", "ededed")
            description = label.get("description", "")

            if name.lower() in existing_by_name:
                existing_label = existing_by_name[name.lower()]
                needs_update = (
                    args.update_existing and (
                        existing_label.get("color") != color.lstrip("#") or
                        existing_label.get("description", "") != description
                    )
                )

                if needs_update:
                    if update_label(target, name, color, description, dry_run=args.dry_run):
                        print(f"  {YELLOW}↻{NC} Updated: {name}")
                        updated += 1
                    else:
                        print(f"  {RED}✗{NC} Failed to update: {name}")
                else:
                    skipped += 1
            else:
                if create_label(target, name, color, description, dry_run=args.dry_run):
                    print(f"  {GREEN}+{NC} Created: {name}")
                    created += 1
                else:
                    print(f"  {RED}✗{NC} Failed to create: {name}")

        # Delete extra labels
        if args.delete_extra:
            for existing_label in existing:
                if existing_label["name"].lower() not in source_by_name:
                    if delete_label(target, existing_label["name"], dry_run=args.dry_run):
                        print(f"  {RED}-{NC} Deleted: {existing_label['name']}")
                        deleted += 1
                    else:
                        print(f"  {RED}✗{NC} Failed to delete: {existing_label['name']}")

        print(f"  Summary: {GREEN}+{created}{NC} created, {YELLOW}↻{updated}{NC} updated, {RED}-{deleted}{NC} deleted, {skipped} skipped")
        print()

    print(f"{GREEN}✓ Labels synced{NC}")
    print()


if __name__ == "__main__":
    main()
