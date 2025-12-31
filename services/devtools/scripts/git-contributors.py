#!/usr/bin/env python3
"""
git-contributors.py - Contributor Statistics
Zeigt Contributor-Statistiken für ein Repository.
"""

import sys
import subprocess
import argparse
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

# Farben
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'
BOLD = '\033[1m'


def run_git(args: List[str], cwd: Optional[str] = None) -> Optional[str]:
    """Run git command."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=cwd
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_contributors(repo_path: str, since: Optional[str] = None, until: Optional[str] = None) -> List[Dict]:
    """Get contributor statistics from git log."""
    args = ["log", "--format=%aN|%aE|%aI", "--no-merges"]

    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")

    output = run_git(args, cwd=repo_path)
    if not output:
        return []

    contributors: Dict[str, Dict] = {}

    for line in output.split("\n"):
        if not line or "|" not in line:
            continue

        parts = line.split("|")
        if len(parts) < 3:
            continue

        name, email, date_str = parts[0], parts[1], parts[2]
        key = email.lower()

        if key not in contributors:
            contributors[key] = {
                "name": name,
                "email": email,
                "commits": 0,
                "first_commit": date_str,
                "last_commit": date_str
            }

        contributors[key]["commits"] += 1
        contributors[key]["last_commit"] = date_str
        # Keep the first commit (chronologically earliest)
        if date_str < contributors[key]["first_commit"]:
            contributors[key]["first_commit"] = date_str

    return sorted(contributors.values(), key=lambda x: x["commits"], reverse=True)


def get_file_stats(repo_path: str, since: Optional[str] = None, until: Optional[str] = None) -> Dict[str, Dict]:
    """Get lines added/removed per contributor."""
    args = ["log", "--format=%aN|%aE", "--numstat", "--no-merges"]

    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")

    output = run_git(args, cwd=repo_path)
    if not output:
        return {}

    stats: Dict[str, Dict] = defaultdict(lambda: {"added": 0, "removed": 0, "files": set()})
    current_author = None

    for line in output.split("\n"):
        if "|" in line and "\t" not in line:
            # Author line
            parts = line.split("|")
            if len(parts) >= 2:
                current_author = parts[1].lower()
        elif "\t" in line and current_author:
            # Stat line: added\tremoved\tfilename
            parts = line.split("\t")
            if len(parts) >= 3:
                added = parts[0]
                removed = parts[1]
                filename = parts[2]

                if added != "-":
                    stats[current_author]["added"] += int(added)
                if removed != "-":
                    stats[current_author]["removed"] += int(removed)
                stats[current_author]["files"].add(filename)

    # Convert sets to counts
    for email in stats:
        stats[email]["files"] = len(stats[email]["files"])

    return dict(stats)


def get_activity_by_day(repo_path: str, since: Optional[str] = None) -> Dict[str, int]:
    """Get commit counts by day of week."""
    args = ["log", "--format=%ad", "--date=format:%A", "--no-merges"]

    if since:
        args.append(f"--since={since}")

    output = run_git(args, cwd=repo_path)
    if not output:
        return {}

    days = defaultdict(int)
    for day in output.split("\n"):
        if day:
            days[day] += 1

    return dict(days)


def get_activity_by_hour(repo_path: str, since: Optional[str] = None) -> Dict[int, int]:
    """Get commit counts by hour."""
    args = ["log", "--format=%ad", "--date=format:%H", "--no-merges"]

    if since:
        args.append(f"--since={since}")

    output = run_git(args, cwd=repo_path)
    if not output:
        return {}

    hours = defaultdict(int)
    for hour in output.split("\n"):
        if hour:
            hours[int(hour)] += 1

    return dict(hours)


def format_date(date_str: str) -> str:
    """Format ISO date to readable format."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str[:10] if len(date_str) >= 10 else date_str


def create_bar(value: int, max_value: int, width: int = 30) -> str:
    """Create ASCII bar chart."""
    if max_value == 0:
        return ""
    filled = int((value / max_value) * width)
    return "█" * filled + "░" * (width - filled)


def main():
    parser = argparse.ArgumentParser(
        description="Show contributor statistics for a repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show contributors for current repo
  git-contributors.py

  # Show contributors for specific repo
  git-contributors.py /path/to/repo

  # Show stats for last 30 days
  git-contributors.py --since "30 days ago"

  # Show detailed stats including lines changed
  git-contributors.py --detailed

  # Show activity patterns
  git-contributors.py --activity

  # Export as JSON
  git-contributors.py --json

  # Show top 10 contributors
  git-contributors.py --limit 10
        """
    )

    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Repository path (default: current directory)"
    )
    parser.add_argument(
        "--since",
        help="Only count commits after this date"
    )
    parser.add_argument(
        "--until",
        help="Only count commits before this date"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed stats (lines added/removed)"
    )
    parser.add_argument(
        "--activity",
        action="store_true",
        help="Show activity patterns"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of contributors shown"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Check if repo is a git repository
    if not run_git(["rev-parse", "--git-dir"], cwd=args.repo):
        print(f"{RED}[ERROR] Not a git repository: {args.repo}{NC}")
        sys.exit(1)

    # Get repo name
    repo_name = run_git(["rev-parse", "--show-toplevel"], cwd=args.repo)
    if repo_name:
        repo_name = repo_name.split("/")[-1].split("\\")[-1]
    else:
        repo_name = args.repo

    # Get contributors
    contributors = get_contributors(args.repo, args.since, args.until)

    if not contributors:
        print(f"{YELLOW}No commits found{NC}")
        sys.exit(0)

    # Get file stats if detailed
    file_stats = {}
    if args.detailed:
        file_stats = get_file_stats(args.repo, args.since, args.until)

    # JSON output
    if args.json_output:
        import json
        output = {
            "repository": repo_name,
            "period": {
                "since": args.since,
                "until": args.until
            },
            "contributors": []
        }

        for c in contributors:
            entry = {
                "name": c["name"],
                "email": c["email"],
                "commits": c["commits"],
                "first_commit": c["first_commit"],
                "last_commit": c["last_commit"]
            }
            if args.detailed and c["email"].lower() in file_stats:
                stats = file_stats[c["email"].lower()]
                entry["lines_added"] = stats["added"]
                entry["lines_removed"] = stats["removed"]
                entry["files_changed"] = stats["files"]
            output["contributors"].append(entry)

        if args.activity:
            output["activity"] = {
                "by_day": get_activity_by_day(args.repo, args.since),
                "by_hour": dict(get_activity_by_hour(args.repo, args.since))
            }

        print(json.dumps(output, indent=2))
        sys.exit(0)

    # Console output
    print()
    print(f"{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║                  Git Contributor Statistics                   ║{NC}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════╝{NC}")
    print()

    print(f"{CYAN}Repository:{NC} {repo_name}")
    if args.since:
        print(f"{CYAN}Since:{NC} {args.since}")
    if args.until:
        print(f"{CYAN}Until:{NC} {args.until}")
    print()

    total_commits = sum(c["commits"] for c in contributors)
    print(f"{BOLD}Contributors: {len(contributors)}{NC}")
    print(f"{BOLD}Total Commits: {total_commits}{NC}")
    print()

    # Apply limit
    display_contributors = contributors
    if args.limit > 0:
        display_contributors = contributors[:args.limit]

    # Find max for bar chart
    max_commits = display_contributors[0]["commits"] if display_contributors else 0

    print(f"{BOLD}{'Contributor':<30} {'Commits':>8}  {'%':>5}  Distribution{NC}")
    print("─" * 80)

    for c in display_contributors:
        name = c["name"][:28]
        commits = c["commits"]
        pct = (commits / total_commits * 100) if total_commits > 0 else 0
        bar = create_bar(commits, max_commits, 20)

        print(f"{name:<30} {commits:>8}  {pct:>5.1f}%  {bar}")

    if args.limit > 0 and len(contributors) > args.limit:
        others = len(contributors) - args.limit
        other_commits = sum(c["commits"] for c in contributors[args.limit:])
        print(f"{'... and ' + str(others) + ' more':<30} {other_commits:>8}")

    # Detailed stats
    if args.detailed and file_stats:
        print()
        print(f"{BOLD}{'Contributor':<30} {'Added':>10} {'Removed':>10} {'Files':>8}{NC}")
        print("─" * 80)

        for c in display_contributors:
            email = c["email"].lower()
            if email in file_stats:
                stats = file_stats[email]
                name = c["name"][:28]
                print(f"{name:<30} {GREEN}+{stats['added']:>9}{NC} {RED}-{stats['removed']:>9}{NC} {stats['files']:>8}")

    # Activity patterns
    if args.activity:
        print()
        print(f"{BOLD}Activity by Day:{NC}")

        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_stats = get_activity_by_day(args.repo, args.since)
        max_day = max(day_stats.values()) if day_stats else 0

        for day in days_order:
            count = day_stats.get(day, 0)
            bar = create_bar(count, max_day, 30)
            print(f"  {day:<10} {bar} {count}")

        print()
        print(f"{BOLD}Activity by Hour:{NC}")

        hour_stats = get_activity_by_hour(args.repo, args.since)
        max_hour = max(hour_stats.values()) if hour_stats else 0

        # Show in 3-hour blocks for compactness
        for start in range(0, 24, 3):
            block_count = sum(hour_stats.get(h, 0) for h in range(start, start + 3))
            bar = create_bar(block_count, max_hour * 3, 20)
            print(f"  {start:02d}:00-{start+2:02d}:59  {bar} {block_count}")

    # Time span info
    if contributors:
        first_commit = min(c["first_commit"] for c in contributors)
        last_commit = max(c["last_commit"] for c in contributors)
        print()
        print(f"{CYAN}First commit:{NC} {format_date(first_commit)}")
        print(f"{CYAN}Last commit:{NC} {format_date(last_commit)}")

    print()


if __name__ == "__main__":
    main()
