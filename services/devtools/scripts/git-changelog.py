#!/usr/bin/env python3
"""
git-changelog.py - Generate Changelog from Git Commits
Erstellt professionelle Changelogs aus Git-Commits nach Conventional Commits Standard.
"""

import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import click
from rich.console import Console
from rich.table import Table

console = Console()

# Conventional Commits Kategorien
COMMIT_TYPES = {
    "feat": ("Features", "✨"),
    "fix": ("Bug Fixes", "🐛"),
    "docs": ("Documentation", "📚"),
    "style": ("Styles", "💎"),
    "refactor": ("Code Refactoring", "♻️"),
    "perf": ("Performance", "⚡"),
    "test": ("Tests", "🧪"),
    "build": ("Build System", "📦"),
    "ci": ("CI/CD", "🔧"),
    "chore": ("Chores", "🔨"),
    "revert": ("Reverts", "⏪"),
    "security": ("Security", "🔒"),
}


def run_git(args: list[str]) -> str:
    """Execute git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git error: {e.stderr}[/red]")
        sys.exit(1)


def get_tags() -> list[str]:
    """Get all tags sorted by version."""
    output = run_git(["tag", "-l", "--sort=-version:refname"])
    return output.split("\n") if output else []


def get_commits_between(from_ref: str | None, to_ref: str) -> list[dict]:
    """Get commits between two refs."""
    if from_ref:
        range_spec = f"{from_ref}..{to_ref}"
    else:
        range_spec = to_ref

    # Format: hash|date|author|subject
    format_str = "%H|%ai|%an|%s"
    output = run_git(["log", range_spec, f"--format={format_str}"])

    commits = []
    for line in output.split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0][:8],
                "date": parts[1].split()[0],
                "author": parts[2],
                "subject": parts[3],
            })
    return commits


def parse_commit(subject: str) -> tuple[str, str, str, bool]:
    """Parse conventional commit message.

    Returns: (type, scope, message, is_breaking)
    """
    # Pattern: type(scope)!: message or type!: message or type: message
    pattern = r"^(\w+)(?:\(([^)]+)\))?(!)?\s*:\s*(.+)$"
    match = re.match(pattern, subject)

    if match:
        commit_type = match.group(1).lower()
        scope = match.group(2) or ""
        is_breaking = bool(match.group(3))
        message = match.group(4)
        return commit_type, scope, message, is_breaking

    return "other", "", subject, False


def group_commits(commits: list[dict]) -> dict[str, list[dict]]:
    """Group commits by type."""
    grouped = defaultdict(list)

    for commit in commits:
        commit_type, scope, message, is_breaking = parse_commit(commit["subject"])
        commit["type"] = commit_type
        commit["scope"] = scope
        commit["message"] = message
        commit["breaking"] = is_breaking

        if commit_type in COMMIT_TYPES:
            grouped[commit_type].append(commit)
        else:
            grouped["other"].append(commit)

    return grouped


def format_markdown(
    version: str,
    date: str,
    grouped_commits: dict[str, list[dict]],
    compare_url: str | None = None,
) -> str:
    """Format changelog entry as Markdown."""
    lines = []

    # Header
    if compare_url:
        lines.append(f"## [{version}]({compare_url}) ({date})")
    else:
        lines.append(f"## {version} ({date})")
    lines.append("")

    # Breaking Changes first
    breaking = []
    for commits in grouped_commits.values():
        for commit in commits:
            if commit.get("breaking"):
                breaking.append(commit)

    if breaking:
        lines.append("### ⚠️ BREAKING CHANGES")
        lines.append("")
        for commit in breaking:
            scope = f"**{commit['scope']}:** " if commit["scope"] else ""
            lines.append(f"- {scope}{commit['message']} ({commit['hash']})")
        lines.append("")

    # Regular sections
    for commit_type, (title, emoji) in COMMIT_TYPES.items():
        if commit_type in grouped_commits and grouped_commits[commit_type]:
            lines.append(f"### {emoji} {title}")
            lines.append("")
            for commit in grouped_commits[commit_type]:
                scope = f"**{commit['scope']}:** " if commit["scope"] else ""
                lines.append(f"- {scope}{commit['message']} ({commit['hash']})")
            lines.append("")

    # Other commits
    if "other" in grouped_commits and grouped_commits["other"]:
        lines.append("### Other Changes")
        lines.append("")
        for commit in grouped_commits["other"]:
            lines.append(f"- {commit['subject']} ({commit['hash']})")
        lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--from", "from_ref",
    help="Starting ref (tag or commit). Default: previous tag",
)
@click.option(
    "--to", "to_ref",
    default="HEAD",
    help="Ending ref (tag or commit). Default: HEAD",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path. Default: stdout",
)
@click.option(
    "--version", "-v", "version_str",
    help="Version string for the changelog header",
)
@click.option(
    "--all-tags", is_flag=True,
    help="Generate changelog for all tags",
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["markdown", "json", "table"]),
    default="markdown",
    help="Output format",
)
def main(
    from_ref: str | None,
    to_ref: str,
    output: str | None,
    version_str: str | None,
    all_tags: bool,
    output_format: str,
):
    """Generate changelog from git commits.

    Examples:

        # Generate changelog since last tag
        git-changelog.py

        # Generate changelog between two tags
        git-changelog.py --from v1.0.0 --to v1.1.0

        # Generate full changelog for all tags
        git-changelog.py --all-tags -o CHANGELOG.md
    """
    # Check if we're in a git repo
    try:
        run_git(["rev-parse", "--git-dir"])
    except SystemExit:
        console.print("[red]Error: Not a git repository[/red]")
        sys.exit(1)

    tags = get_tags()
    changelog_parts = []

    if all_tags:
        # Generate changelog for all tags
        console.print("[cyan]Generating changelog for all tags...[/cyan]")

        for i, tag in enumerate(tags):
            prev_tag = tags[i + 1] if i + 1 < len(tags) else None
            commits = get_commits_between(prev_tag, tag)

            if commits:
                # Get tag date
                tag_date = run_git(["log", "-1", "--format=%ai", tag]).split()[0]
                grouped = group_commits(commits)
                changelog_parts.append(
                    format_markdown(tag, tag_date, grouped)
                )

        # Unreleased changes
        if tags:
            unreleased = get_commits_between(tags[0], "HEAD")
            if unreleased:
                grouped = group_commits(unreleased)
                changelog_parts.insert(
                    0,
                    format_markdown("Unreleased", datetime.now().strftime("%Y-%m-%d"), grouped)
                )

    else:
        # Single changelog entry
        if not from_ref and tags:
            from_ref = tags[0]
            console.print(f"[cyan]Using {from_ref} as starting point[/cyan]")

        commits = get_commits_between(from_ref, to_ref)

        if not commits:
            console.print("[yellow]No commits found in range[/yellow]")
            sys.exit(0)

        grouped = group_commits(commits)
        version = version_str or "Unreleased"
        date = datetime.now().strftime("%Y-%m-%d")

        if output_format == "table":
            # Rich table output
            table = Table(title=f"Changelog: {version}")
            table.add_column("Type", style="cyan")
            table.add_column("Scope", style="yellow")
            table.add_column("Message")
            table.add_column("Hash", style="dim")

            for commit in commits:
                commit_type, scope, message, _ = parse_commit(commit["subject"])
                table.add_row(commit_type, scope, message, commit["hash"])

            console.print(table)
            return

        elif output_format == "json":
            import json
            result = {
                "version": version,
                "date": date,
                "commits": [
                    {
                        "hash": c["hash"],
                        "type": parse_commit(c["subject"])[0],
                        "scope": parse_commit(c["subject"])[1],
                        "message": parse_commit(c["subject"])[2],
                        "breaking": parse_commit(c["subject"])[3],
                    }
                    for c in commits
                ],
            }
            print(json.dumps(result, indent=2))
            return

        changelog_parts.append(format_markdown(version, date, grouped))

    # Output
    changelog = "\n".join(changelog_parts)

    if output:
        output_path = Path(output)

        if output_path.exists():
            # Prepend to existing file
            existing = output_path.read_text()
            # Find header and insert after
            if existing.startswith("# "):
                header_end = existing.find("\n\n")
                if header_end > 0:
                    changelog = (
                        existing[: header_end + 2]
                        + changelog
                        + "\n"
                        + existing[header_end + 2:]
                    )
                else:
                    changelog = existing + "\n" + changelog
            else:
                changelog = changelog + "\n" + existing

        output_path.write_text(changelog)
        console.print(f"[green]✓ Changelog written to {output}[/green]")
    else:
        print(changelog)


if __name__ == "__main__":
    main()
