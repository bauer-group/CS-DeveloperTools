#!/usr/bin/env python3
# @name: git-split-repo
# @description: Split monorepo into separate repositories
# @category: git
# @usage: git-split-repo.py <folder> [--target <url>]
"""
git-split-repo.py - Split Monorepo into Separate Repositories
Extrahiert Unterordner in eigene Repositories mit vollständiger Historie.
"""

import os
import sys
import re
import shutil
import tempfile
import argparse
import subprocess
from pathlib import Path

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'


def run(cmd: list, cwd: str = None, check: bool = True, capture: bool = False):
    """Execute command and optionally capture output."""
    cmd_str = ' '.join(cmd)
    print(f"{CYAN}→{NC} {cmd_str}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        capture_output=capture,
        text=True
    )

    if capture:
        return result.stdout.strip()
    return result.returncode == 0


def normalize_name(name: str) -> str:
    """Normalize folder name to valid repo name."""
    return re.sub(r'[^a-zA-Z0-9._-]+', '-', name).strip('-').lower()


def check_dependencies():
    """Check required tools."""
    if not shutil.which("git-filter-repo"):
        print(f"{RED}[ERROR] git-filter-repo not found{NC}")
        print("Install with: pip install git-filter-repo")
        sys.exit(1)

    if not shutil.which("gh"):
        print(f"{YELLOW}[WARNING] gh CLI not found - GitHub operations will fail{NC}")


def check_git_repo(path: str):
    """Verify we're in a git repository."""
    git_dir = Path(path) / ".git"
    if not git_dir.exists():
        print(f"{RED}[ERROR] Not a git repository: {path}{NC}")
        sys.exit(1)


def get_commit_hash(repo_dir: str) -> str:
    """Get current HEAD commit hash."""
    return run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture=True)


def split_folder(
    monorepo_path: str,
    folder: str,
    github_org: str,
    repo_name: str = None,
    as_submodule: bool = False,
    dry_run: bool = False,
    private: bool = True
):
    """Split a folder into its own repository."""
    folder = folder.strip("/\\")
    repo_name = repo_name or normalize_name(Path(folder).name)
    full_path = Path(monorepo_path) / folder

    if not full_path.exists():
        print(f"{RED}[ERROR] Folder not found: {folder}{NC}")
        return False

    print()
    print(f"{BOLD}{CYAN}═══ Splitting: {folder} ═══{NC}")
    print(f"Target repo: {github_org}/{repo_name}")
    print()

    if dry_run:
        print(f"{YELLOW}DRY RUN - Would create: {github_org}/{repo_name}{NC}")
        return True

    # Step 1: Clone to temp directory
    temp_dir = tempfile.mkdtemp(prefix=f"{repo_name}_split_")
    print(f"Cloning to temp directory: {temp_dir}")

    try:
        run(["git", "clone", "--no-local", ".", temp_dir], cwd=monorepo_path)

        # Step 2: Filter to subdirectory only
        print()
        print("Filtering history to subdirectory...")
        run(["git", "filter-repo", "--subdirectory-filter", folder, "--force"], cwd=temp_dir)

        # Step 3: Create GitHub repo
        print()
        print("Creating GitHub repository...")
        visibility = "--private" if private else "--public"
        run(["gh", "repo", "create", f"{github_org}/{repo_name}", visibility, "--confirm"], cwd=temp_dir)

        # Step 4: Add remote
        https_url = f"https://github.com/{github_org}/{repo_name}.git"
        run(["git", "remote", "add", "origin", https_url], cwd=temp_dir)

        # Step 5: Push
        print()
        print("Pushing to GitHub...")
        run(["git", "branch", "-M", "main"], cwd=temp_dir)
        run(["git", "push", "-u", "origin", "main"], cwd=temp_dir)

        commit_hash = get_commit_hash(temp_dir)

        # Step 6: Optionally convert to submodule
        if as_submodule:
            print()
            print("Converting to submodule in monorepo...")

            # Remove original folder
            if full_path.is_dir():
                shutil.rmtree(full_path)

            # Add as submodule
            run(["git", "submodule", "add", "-b", "main", https_url, folder], cwd=monorepo_path)
            run(["git", "fetch"], cwd=str(full_path))
            run(["git", "checkout", commit_hash], cwd=str(full_path))
            run(["git", "add", ".gitmodules", folder], cwd=monorepo_path)
            run(["git", "commit", "-m", f"Replace {folder} with submodule at {commit_hash[:8]}"], cwd=monorepo_path)

        print(f"{GREEN}✓ Successfully created: {github_org}/{repo_name}{NC}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"{RED}[ERROR] Failed: {e}{NC}")
        return False

    finally:
        # Cleanup temp directory
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="Split monorepo folders into separate GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Split single folder
  git-split-repo.py -o my-org libs/my-lib

  # Split multiple folders
  git-split-repo.py -o my-org libs/libA libs/libB tools/toolX

  # Split and convert to submodules
  git-split-repo.py -o my-org --submodule libs/my-lib

  # Preview without making changes
  git-split-repo.py -o my-org --dry-run libs/my-lib
        """
    )

    parser.add_argument(
        "folders",
        nargs="+",
        help="Folders to split into separate repos"
    )
    parser.add_argument(
        "-o", "--org",
        required=True,
        help="GitHub organization or username"
    )
    parser.add_argument(
        "-r", "--repo",
        help="Custom repository name (only for single folder)"
    )
    parser.add_argument(
        "-p", "--path",
        default=".",
        help="Path to monorepo (default: current directory)"
    )
    parser.add_argument(
        "-s", "--submodule",
        action="store_true",
        help="Replace folder with submodule after splitting"
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Create public repositories (default: private)"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be done without changes"
    )

    args = parser.parse_args()

    # Validate
    if args.repo and len(args.folders) > 1:
        print(f"{RED}[ERROR] --repo can only be used with a single folder{NC}")
        sys.exit(1)

    monorepo_path = os.path.abspath(args.path)

    check_dependencies()
    check_git_repo(monorepo_path)

    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                  Git Split Repository Tool                    ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()
    print(f"Monorepo: {monorepo_path}")
    print(f"Target org: {args.org}")
    print(f"Folders: {', '.join(args.folders)}")
    print(f"Submodule: {args.submodule}")
    print(f"Visibility: {'public' if args.public else 'private'}")

    if args.dry_run:
        print(f"{YELLOW}DRY RUN MODE{NC}")

    success_count = 0
    for folder in args.folders:
        repo_name = args.repo if args.repo else None
        if split_folder(
            monorepo_path,
            folder,
            args.org,
            repo_name=repo_name,
            as_submodule=args.submodule,
            dry_run=args.dry_run,
            private=not args.public
        ):
            success_count += 1

    # Push monorepo if submodules were added
    if args.submodule and not args.dry_run and success_count > 0:
        print()
        print("Pushing monorepo with submodule changes...")
        run(["git", "push"], cwd=monorepo_path)

    print()
    print(f"{GREEN}═══ Complete: {success_count}/{len(args.folders)} folders processed ═══{NC}")


if __name__ == "__main__":
    main()
