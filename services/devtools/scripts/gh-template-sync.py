#!/usr/bin/env python3
# @name: gh-template-sync
# @description: Sync issue and PR templates across organization repositories
# @category: github
# @usage: gh-template-sync.py [-o <org>] --source <repo> [--execute]
"""
gh-template-sync.py - Template Sync Tool
Synchronisiert Issue und PR Templates über alle Repositories einer Organisation.
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

# Template file patterns
TEMPLATE_FILES = [
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/PULL_REQUEST_TEMPLATE/pull_request_template.md",
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


def get_templates(org: str, repo: str, branch: str = "main") -> Dict[str, str]:
    """Get all template files from a repository."""
    templates = {}
    for path in TEMPLATE_FILES:
        content = get_file_content(org, repo, path, branch)
        if content:
            templates[path] = content
    return templates


def get_all_template_files(org: str, repo: str, branch: str = "main") -> List[str]:
    """Get all files in .github/ISSUE_TEMPLATE directory."""
    output = run_gh(["api", f"repos/{org}/{repo}/contents/.github/ISSUE_TEMPLATE?ref={branch}"])
    if not output:
        return []

    try:
        files = json.loads(output)
        return [f".github/ISSUE_TEMPLATE/{f['name']}" for f in files if f["type"] == "file"]
    except (json.JSONDecodeError, KeyError):
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Sync issue and PR templates across organization repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List template status across repos
  gh-template-sync.py --list

  # Sync all templates from source repo
  gh-template-sync.py --source template-repo --execute

  # Sync to specific repos only
  gh-template-sync.py --source template-repo --target repo1,repo2 --execute

  # Sync only issue templates
  gh-template-sync.py --source template-repo --type issue --execute

  # Sync only PR template
  gh-template-sync.py --source template-repo --type pr --execute

  # Export current template status
  gh-template-sync.py --export
        """
    )

    parser.add_argument(
        "-o", "--org",
        default="bauer-group",
        help="GitHub organization (default: bauer-group)"
    )
    parser.add_argument(
        "--source",
        help="Source repository for templates"
    )
    parser.add_argument(
        "--target",
        help="Comma-separated list of target repos (default: all)"
    )
    parser.add_argument(
        "--type",
        choices=["all", "issue", "pr"],
        default="all",
        help="Type of templates to sync (default: all)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List template status across repos"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export template status as JSON"
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
        print(f"{BOLD}{CYAN}|                   Template Sync Tool                          |{NC}")
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

    # Collect template status
    status = []
    for repo in repos:
        repo_name = repo["name"]
        default_branch = repo.get("default_branch", "main")
        templates = get_templates(args.org, repo_name, default_branch)

        has_issue_templates = any(p.startswith(".github/ISSUE_TEMPLATE") for p in templates.keys())
        has_pr_template = any("PULL_REQUEST" in p for p in templates.keys())

        status.append({
            "name": repo_name,
            "branch": default_branch,
            "has_issue_templates": has_issue_templates,
            "has_pr_template": has_pr_template,
            "templates": list(templates.keys()),
            "template_contents": templates
        })

    # Export mode
    if args.export:
        # Remove content for cleaner export
        export_status = [{k: v for k, v in s.items() if k != "template_contents"} for s in status]
        print(json.dumps(export_status, indent=2))
        return

    # List mode
    if args.list:
        print(f"{BOLD}Template Status:{NC}")
        print()

        for s in status:
            issue_status = f"{GREEN}✓{NC}" if s["has_issue_templates"] else f"{RED}✗{NC}"
            pr_status = f"{GREEN}✓{NC}" if s["has_pr_template"] else f"{RED}✗{NC}"
            print(f"  {s['name']}: Issue {issue_status}  PR {pr_status}")
            if s["templates"]:
                for t in s["templates"]:
                    print(f"    {DIM}- {t}{NC}")

        # Summary
        with_issue = len([s for s in status if s["has_issue_templates"]])
        with_pr = len([s for s in status if s["has_pr_template"]])

        print()
        print(f"Issue templates: {with_issue}/{len(status)} repos")
        print(f"PR templates: {with_pr}/{len(status)} repos")
        return

    # Sync mode requires source
    if not args.source:
        print(f"{YELLOW}Use --list to see status, or --source to sync{NC}")
        return

    # Get source templates
    source_repo = next((r for r in repos if r["name"] == args.source), None)
    if not source_repo:
        print(f"{RED}[ERROR] Source repo not found: {args.source}{NC}")
        sys.exit(1)

    source_status = next((s for s in status if s["name"] == args.source), None)
    if not source_status or not source_status["templates"]:
        print(f"{RED}[ERROR] No templates found in source repo{NC}")
        sys.exit(1)

    # Filter templates by type
    source_templates = source_status["template_contents"]
    if args.type == "issue":
        source_templates = {k: v for k, v in source_templates.items() if "ISSUE_TEMPLATE" in k}
    elif args.type == "pr":
        source_templates = {k: v for k, v in source_templates.items() if "PULL_REQUEST" in k}

    print(f"Source: {BOLD}{args.source}{NC}")
    print(f"Templates to sync: {len(source_templates)}")
    for path in source_templates.keys():
        print(f"  - {path}")
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
    synced_repos = 0
    synced_files = 0
    skipped = 0
    failed = 0

    for target in targets:
        target_name = target["name"]
        target_status = next((s for s in status if s["name"] == target_name), None)
        repo_synced = False

        for path, content in source_templates.items():
            # Check if content is same
            existing_content = target_status["template_contents"].get(path) if target_status else None
            if existing_content == content:
                skipped += 1
                continue

            # Sync file
            success = create_or_update_file(
                args.org, target_name, path, content,
                "chore: sync templates from template repo",
                target.get("default_branch", "main"),
                dry_run
            )

            if success:
                action = "would sync" if dry_run else "synced"
                print(f"  {GREEN}✓{NC} {target_name}: {path} ({action})")
                synced_files += 1
                repo_synced = True
            else:
                print(f"  {RED}✗{NC} {target_name}: {path} (failed)")
                failed += 1

        if repo_synced:
            synced_repos += 1

    # Summary
    print()
    print(f"Repos updated: {GREEN}{synced_repos}{NC}")
    print(f"Files synced: {GREEN}{synced_files}{NC}, Skipped: {skipped}, Failed: {RED}{failed}{NC}")

    if dry_run and synced_files > 0:
        print()
        print(f"Run with {BOLD}--execute{NC} to apply changes.")


if __name__ == "__main__":
    main()
