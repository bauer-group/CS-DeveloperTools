#!/usr/bin/env python3
# @name: git-release
# @description: Manage releases with semantic versioning
# @category: git
# @usage: git-release.py [major|minor|patch] [--dry-run]
"""
git-release.py - Semantic Versioning Release Manager
Verwaltet Releases nach Semantic Versioning (semver.org).
"""

import subprocess
import sys
import re
from enum import Enum

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class BumpType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PREMAJOR = "premajor"
    PREMINOR = "preminor"
    PREPATCH = "prepatch"
    PRERELEASE = "prerelease"


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Execute git command."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        console.print(f"[red]Git error: {result.stderr}[/red]")
        sys.exit(1)
    return result


def get_current_version() -> str | None:
    """Get current version from latest tag."""
    result = run_git(["describe", "--tags", "--abbrev=0"], check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def parse_version(version: str) -> tuple[int, int, int, str | None, int | None]:
    """Parse semver string.

    Returns: (major, minor, patch, prerelease_type, prerelease_num)
    """
    # Remove 'v' prefix if present
    version = version.lstrip("v")

    # Pattern: major.minor.patch[-prerelease.num]
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z]+)\.?(\d+)?)?$"
    match = re.match(pattern, version)

    if not match:
        console.print(f"[red]Invalid version format: {version}[/red]")
        sys.exit(1)

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    pre_type = match.group(4)
    pre_num = int(match.group(5)) if match.group(5) else None

    return major, minor, patch, pre_type, pre_num


def format_version(
    major: int,
    minor: int,
    patch: int,
    pre_type: str | None = None,
    pre_num: int | None = None,
    prefix: str = "v",
) -> str:
    """Format version components to string."""
    version = f"{prefix}{major}.{minor}.{patch}"
    if pre_type:
        version += f"-{pre_type}"
        if pre_num is not None:
            version += f".{pre_num}"
    return version


def bump_version(
    current: str,
    bump_type: BumpType,
    preid: str = "alpha",
) -> str:
    """Calculate new version based on bump type."""
    major, minor, patch, pre_type, pre_num = parse_version(current)
    prefix = "v" if current.startswith("v") else ""

    if bump_type == BumpType.MAJOR:
        return format_version(major + 1, 0, 0, prefix=prefix)
    elif bump_type == BumpType.MINOR:
        return format_version(major, minor + 1, 0, prefix=prefix)
    elif bump_type == BumpType.PATCH:
        if pre_type:
            # If currently prerelease, just remove prerelease
            return format_version(major, minor, patch, prefix=prefix)
        return format_version(major, minor, patch + 1, prefix=prefix)
    elif bump_type == BumpType.PREMAJOR:
        return format_version(major + 1, 0, 0, preid, 0, prefix)
    elif bump_type == BumpType.PREMINOR:
        return format_version(major, minor + 1, 0, preid, 0, prefix)
    elif bump_type == BumpType.PREPATCH:
        return format_version(major, minor, patch + 1, preid, 0, prefix)
    elif bump_type == BumpType.PRERELEASE:
        if pre_type:
            # Increment prerelease number
            new_pre_num = (pre_num or 0) + 1
            return format_version(major, minor, patch, pre_type, new_pre_num, prefix)
        else:
            # Create new prerelease
            return format_version(major, minor, patch + 1, preid, 0, prefix)

    return current


def get_commits_since_tag(tag: str | None) -> list[dict]:
    """Get commits since tag."""
    if tag:
        range_spec = f"{tag}..HEAD"
    else:
        range_spec = "HEAD"

    result = run_git(["log", range_spec, "--format=%H|%s"])
    commits = []

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0][:8], "subject": parts[1]})

    return commits


def analyze_commits(commits: list[dict]) -> BumpType:
    """Analyze commits to suggest bump type."""
    has_breaking = False
    has_feat = False

    for commit in commits:
        subject = commit["subject"].lower()

        # Check for breaking changes
        if "!" in subject.split(":")[0] or "breaking" in subject:
            has_breaking = True

        # Check for features
        if subject.startswith("feat"):
            has_feat = True

    if has_breaking:
        return BumpType.MAJOR
    elif has_feat:
        return BumpType.MINOR
    else:
        return BumpType.PATCH


def create_tag(version: str, message: str | None = None, sign: bool = False):
    """Create git tag."""
    args = ["tag"]

    if sign:
        args.append("-s")
    else:
        args.append("-a")

    args.append(version)

    if message:
        args.extend(["-m", message])
    else:
        args.extend(["-m", f"Release {version}"])

    run_git(args)


@click.group()
def cli():
    """Git Release Manager - Semantic Versioning Tool"""
    pass


@cli.command()
def current():
    """Show current version."""
    version = get_current_version()
    if version:
        console.print(f"Current version: [green]{version}[/green]")
    else:
        console.print("[yellow]No version tags found[/yellow]")


@cli.command()
def next():
    """Show suggested next version based on commits."""
    current_version = get_current_version()

    if not current_version:
        console.print("[yellow]No version tags found. Suggested: v0.1.0[/yellow]")
        return

    commits = get_commits_since_tag(current_version)

    if not commits:
        console.print("[yellow]No new commits since last release[/yellow]")
        return

    suggested_bump = analyze_commits(commits)
    next_version = bump_version(current_version, suggested_bump)

    console.print(f"Current version:  [cyan]{current_version}[/cyan]")
    console.print(f"Commits since:    [cyan]{len(commits)}[/cyan]")
    console.print(f"Suggested bump:   [yellow]{suggested_bump.value}[/yellow]")
    console.print(f"Next version:     [green]{next_version}[/green]")


@cli.command()
@click.argument("bump_type", type=click.Choice([b.value for b in BumpType]))
@click.option("--preid", default="alpha", help="Prerelease identifier")
@click.option("--message", "-m", help="Tag message")
@click.option("--sign", "-s", is_flag=True, help="GPG sign the tag")
@click.option("--dry-run", "-d", is_flag=True, help="Show what would happen")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def bump(
    bump_type: str,
    preid: str,
    message: str | None,
    sign: bool,
    dry_run: bool,
    yes: bool,
):
    """Bump version and create tag.

    BUMP_TYPE: major, minor, patch, premajor, preminor, prepatch, prerelease
    """
    current_version = get_current_version() or "v0.0.0"
    new_version = bump_version(current_version, BumpType(bump_type), preid)

    console.print(f"Current version: [cyan]{current_version}[/cyan]")
    console.print(f"New version:     [green]{new_version}[/green]")

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/yellow]")
        return

    if not yes:
        if not Confirm.ask(f"Create tag {new_version}?"):
            console.print("[yellow]Aborted[/yellow]")
            return

    # Check for uncommitted changes
    result = run_git(["status", "--porcelain"], check=False)
    if result.stdout.strip():
        console.print("[yellow]Warning: You have uncommitted changes[/yellow]")
        if not yes and not Confirm.ask("Continue anyway?"):
            console.print("[yellow]Aborted[/yellow]")
            return

    create_tag(new_version, message, sign)
    console.print(f"[green]✓ Created tag {new_version}[/green]")
    console.print(f"\nTo push: [cyan]git push origin {new_version}[/cyan]")


@cli.command()
@click.option("--push", "-p", is_flag=True, help="Also push to remote")
def release(push: bool):
    """Interactive release wizard."""
    console.print("\n[bold cyan]🚀 Release Wizard[/bold cyan]\n")

    # Get current state
    current_version = get_current_version()
    if current_version:
        console.print(f"Current version: [cyan]{current_version}[/cyan]")
        commits = get_commits_since_tag(current_version)
        console.print(f"Commits since:   [cyan]{len(commits)}[/cyan]")
    else:
        console.print("[yellow]No existing versions found[/yellow]")
        commits = get_commits_since_tag(None)

    if not commits:
        console.print("\n[yellow]No new commits to release[/yellow]")
        return

    # Show recent commits
    console.print("\n[bold]Recent commits:[/bold]")
    table = Table()
    table.add_column("Hash", style="dim")
    table.add_column("Message")

    for commit in commits[:10]:
        table.add_row(commit["hash"], commit["subject"])

    console.print(table)

    if len(commits) > 10:
        console.print(f"[dim]... and {len(commits) - 10} more[/dim]")

    # Suggest bump type
    suggested_bump = analyze_commits(commits)
    console.print(f"\n[bold]Suggested bump:[/bold] [yellow]{suggested_bump.value}[/yellow]")

    # Ask for bump type
    bump_type = Prompt.ask(
        "Select bump type",
        choices=[b.value for b in BumpType],
        default=suggested_bump.value,
    )

    # Calculate new version
    base_version = current_version or "v0.0.0"
    new_version = bump_version(base_version, BumpType(bump_type))

    console.print(f"\nNew version: [green]{new_version}[/green]")

    # Confirm
    if not Confirm.ask("Create this release?"):
        console.print("[yellow]Aborted[/yellow]")
        return

    # Create tag
    create_tag(new_version)
    console.print(f"[green]✓ Created tag {new_version}[/green]")

    # Push if requested
    if push:
        run_git(["push", "origin", new_version])
        console.print(f"[green]✓ Pushed {new_version} to origin[/green]")
    else:
        console.print(f"\nTo push: [cyan]git push origin {new_version}[/cyan]")


@cli.command()
def list():
    """List all version tags."""
    result = run_git(["tag", "-l", "--sort=-version:refname"])
    tags = result.stdout.strip().split("\n")

    if not tags or tags == [""]:
        console.print("[yellow]No version tags found[/yellow]")
        return

    table = Table(title="Version Tags")
    table.add_column("Version", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Message")

    for tag in tags[:20]:
        if not tag:
            continue
        date_result = run_git(["log", "-1", "--format=%ai", tag])
        date = date_result.stdout.strip().split()[0]

        msg_result = run_git(["tag", "-l", "-n1", tag])
        msg = msg_result.stdout.strip().replace(tag, "").strip()

        table.add_row(tag, date, msg[:50])

    console.print(table)

    if len(tags) > 20:
        console.print(f"[dim]... and {len(tags) - 20} more[/dim]")


if __name__ == "__main__":
    cli()
