#!/usr/bin/env python3
# @name: gh-add-workflow
# @description: Add workflow files to GitHub repositories
# @category: github
# @usage: gh-add-workflow.py <workflow-file> [--topic <topic>] [--repos <list>]
"""
gh-add-workflow.py - Add Workflow Files to GitHub Repositories
Fügt Workflow-Dateien zu Repositories hinzu (nach Topic, Pattern oder Liste).
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional

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


def get_repos(org: str, topic: Optional[str] = None, pattern: Optional[str] = None,
              limit: int = 200) -> List[Dict]:
    """Get list of repositories."""
    args = ["repo", "list", org, "--json", "name,nameWithOwner,defaultBranchRef", "--limit", str(limit)]

    output = run_gh(args)
    if not output:
        return []

    repos = json.loads(output)

    # Filter by topic if specified
    if topic:
        filtered = []
        for repo in repos:
            topics_output = run_gh(["repo", "view", repo["nameWithOwner"], "--json", "repositoryTopics"])
            if topics_output:
                topics_data = json.loads(topics_output)
                repo_topics = [t["name"] for t in topics_data.get("repositoryTopics", [])]
                if topic in repo_topics:
                    filtered.append(repo)
        repos = filtered

    # Filter by pattern if specified
    if pattern:
        import fnmatch
        repos = [r for r in repos if fnmatch.fnmatch(r["name"], pattern)]

    return repos


def file_exists_in_repo(repo: str, file_path: str) -> bool:
    """Check if a file exists in the repository."""
    result = run_gh(["api", f"repos/{repo}/contents/{file_path}", "--silent"])
    return result is not None


def add_file_to_repo(repo: str, file_path: str, content: str, message: str,
                     branch: Optional[str] = None, dry_run: bool = False) -> bool:
    """Add a file to a repository."""
    if dry_run:
        return True

    # Get default branch if not specified
    if not branch:
        repo_info = run_gh(["repo", "view", repo, "--json", "defaultBranchRef"])
        if repo_info:
            data = json.loads(repo_info)
            branch = data.get("defaultBranchRef", {}).get("name", "main")
        else:
            branch = "main"

    # Base64 encode content
    import base64
    content_b64 = base64.b64encode(content.encode()).decode()

    # Create file via API
    api_path = f"repos/{repo}/contents/{file_path}"
    payload = {
        "message": message,
        "content": content_b64,
        "branch": branch
    }

    try:
        result = subprocess.run(
            ["gh", "api", api_path, "-X", "PUT", "-f", f"message={message}",
             "-f", f"content={content_b64}", "-f", f"branch={branch}"],
            capture_output=True, text=True, check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"{RED}  API Error: {e.stderr}{NC}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Add workflow files to GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add workflow from file to repos with specific topic
  gh-add-workflow.py -o myorg --topic python-projects -f ci.yml

  # Add workflow to repos matching pattern
  gh-add-workflow.py -o myorg --pattern "api-*" -f deploy.yml

  # Add workflow to specific repo
  gh-add-workflow.py myorg/myrepo -f build.yml

  # Preview what would be added (dry run)
  gh-add-workflow.py -o myorg --topic backend -f ci.yml --dry-run

  # Add inline workflow content
  gh-add-workflow.py myorg/myrepo --content "name: CI\\non: push\\njobs:..." --name ci.yml

  # Skip repos that already have the workflow
  gh-add-workflow.py -o myorg --topic api -f deploy.yml --skip-existing
        """
    )

    parser.add_argument(
        "repo",
        nargs="?",
        help="Specific repository (owner/name)"
    )
    parser.add_argument(
        "-o", "--org",
        help="Organization name for bulk operations"
    )
    parser.add_argument(
        "--topic",
        help="Filter repos by topic"
    )
    parser.add_argument(
        "--pattern",
        help="Filter repos by name pattern (e.g., 'api-*')"
    )
    parser.add_argument(
        "-f", "--file",
        help="Path to local workflow file to add"
    )
    parser.add_argument(
        "--content",
        help="Inline workflow content (alternative to --file)"
    )
    parser.add_argument(
        "-n", "--name",
        help="Workflow file name (default: from --file or 'workflow.yml')"
    )
    parser.add_argument(
        "-m", "--message",
        default="Add GitHub Actions workflow",
        help="Commit message"
    )
    parser.add_argument(
        "--target-path",
        default=".github/workflows",
        help="Target directory in repo (default: .github/workflows)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip repos that already have the workflow file"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing workflow files"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be added without making changes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max repos to process (default: 200)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.file and not args.content:
        print(f"{RED}[ERROR] Either --file or --content is required{NC}")
        sys.exit(1)

    if not args.repo and not args.org:
        print(f"{RED}[ERROR] Specify either a repo or --org{NC}")
        sys.exit(1)

    # Check authentication
    if not check_gh_auth():
        print(f"{RED}[ERROR] GitHub CLI not authenticated{NC}")
        print("Run: gh auth login")
        sys.exit(1)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                  GitHub Workflow Adder                        ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    # Load workflow content
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"{RED}[ERROR] File not found: {args.file}{NC}")
            sys.exit(1)
        workflow_content = file_path.read_text(encoding="utf-8")
        workflow_name = args.name or file_path.name
    else:
        workflow_content = args.content
        workflow_name = args.name or "workflow.yml"

    # Ensure .yml extension
    if not workflow_name.endswith((".yml", ".yaml")):
        workflow_name += ".yml"

    target_file = f"{args.target_path}/{workflow_name}"

    print(f"{CYAN}Workflow:{NC} {workflow_name}")
    print(f"{CYAN}Target:{NC} {target_file}")
    print()

    # Get target repositories
    repos = []
    if args.repo:
        repos = [{"nameWithOwner": args.repo, "name": args.repo.split("/")[-1]}]
    else:
        print(f"Fetching repositories from {args.org}...")
        repos = get_repos(args.org, topic=args.topic, pattern=args.pattern, limit=args.limit)
        print(f"Found {len(repos)} repositories")
        print()

    if not repos:
        print(f"{YELLOW}No repositories found{NC}")
        sys.exit(0)

    if args.dry_run:
        print(f"{YELLOW}DRY RUN - No changes will be made{NC}")
        print()

    # Process repositories
    added = 0
    skipped = 0
    failed = 0

    for repo in repos:
        repo_name = repo["nameWithOwner"]
        print(f"{CYAN}→{NC} {repo_name}...", end=" ")

        # Check if file exists
        exists = file_exists_in_repo(repo_name, target_file)

        if exists and args.skip_existing:
            print(f"{YELLOW}skipped (exists){NC}")
            skipped += 1
            continue

        if exists and not args.overwrite:
            print(f"{YELLOW}exists (use --overwrite to replace){NC}")
            skipped += 1
            continue

        if args.dry_run:
            action = "would overwrite" if exists else "would add"
            print(f"{GREEN}{action}{NC}")
            added += 1
            continue

        # Add/update the file
        if add_file_to_repo(repo_name, target_file, workflow_content, args.message):
            action = "updated" if exists else "added"
            print(f"{GREEN}✓ {action}{NC}")
            added += 1
        else:
            print(f"{RED}✗ failed{NC}")
            failed += 1

    # Summary
    print()
    print(f"{GREEN}✓ {added} workflows {'would be ' if args.dry_run else ''}added{NC}")
    if skipped:
        print(f"{YELLOW}○ {skipped} skipped{NC}")
    if failed:
        print(f"{RED}✗ {failed} failed{NC}")
    print()


if __name__ == "__main__":
    main()
