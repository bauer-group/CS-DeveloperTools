# DevTools - Swiss Army Knife for Git-based Development

A collection of Docker-based developer tools for Git workflows and development automation. All tools run in isolated containers for platform independence.

## Services

This repository contains independent tools that can be used separately:

| Service | Description | Location |
|---------|-------------|----------|
| **DevTools** | Git & Python runtime container | `./devtools.sh` |
| **Dozzle** | Docker container log viewer | `services/dozzle/` |

## DevTools Runtime Container

Interactive container with Git, Python 3.12, and shell utilities for Git-based development workflows.

### Features

- **Git Tools** - Advanced Git commands, statistics, history rewriting, and automation
- **GitHub Tools** - Repository management, topics, archiving, and workflow triggers
- **Python Environment** - Full Python 3.12 with common libraries (GitPython, Click, Rich, etc.)
- **Shell Utilities** - curl, jq, yq, git-filter-repo, GitHub CLI, and more
- **Platform Independent** - Runs identically on Windows, macOS, and Linux
- **Auto-configured** - Git credentials from host, helpful aliases pre-installed

### Quick Start

```powershell
# Build the container
.\devtools.ps1 build

# Start interactive shell in current directory
.\devtools.ps1 shell

# Start shell in a specific project
.\devtools.ps1 shell C:\Projects\MyApp
```

### Commands

#### Runtime Container

| Command | Description |
|---------|-------------|
| `shell [PATH]` | Start interactive DevTools shell |
| `run <script>` | Run a script in the container |
| `build` | Build/rebuild DevTools container |

#### Git Tools

| Command | Description |
|---------|-------------|
| `stats [PATH]` | Show repository statistics |
| `cleanup [PATH]` | Clean up branches and cache |
| `changelog` | Generate changelog from commits |
| `release` | Manage semantic versioning releases |
| `lfs-migrate` | Migrate repository to Git LFS |
| `history-clean` | Remove large files from git history |
| `branch-rename` | Rename git branches (local + remote) |
| `split-repo` | Split monorepo into separate repos |
| `rewrite-commits` | Rewrite commit messages (pattern-based) |

#### GitHub Tools

| Command | Description |
|---------|-------------|
| `gh-create` | Create GitHub repository |
| `gh-topics` | Manage repository topics |
| `gh-archive` | Archive repositories by criteria |
| `gh-workflow` | Trigger GitHub Actions workflows |

### Tool Details

#### Git History Tools

```bash
# Remove large files from history (requires git-filter-repo)
./devtools.sh history-clean --analyze              # Show large files
./devtools.sh history-clean -s 50M --dry-run       # Preview cleanup

# Rename branches (master → main)
./devtools.sh branch-rename --master-to-main       # Full migration
./devtools.sh branch-rename old-name new-name      # Custom rename

# Split monorepo into separate repos
./devtools.sh split-repo dir1,dir2 -o myorg        # Split to GitHub
./devtools.sh split-repo services/api --submodule  # Keep as submodule

# Rewrite commit messages (remove AI attributions, etc.)
./devtools.sh rewrite-commits --preset claude --dry-run
./devtools.sh rewrite-commits --preset ai-all
./devtools.sh rewrite-commits -p "TICKET-\d+:\s*"  # Custom pattern
```

#### GitHub Management Tools

```bash
# Create repository
./devtools.sh gh-create myrepo --public --init
./devtools.sh gh-create -o myorg myrepo -t "python,cli" --license MIT

# Manage topics across repos
./devtools.sh gh-topics -o myorg --analyze           # Topic statistics
./devtools.sh gh-topics -o myorg --add python,api    # Add to all repos
./devtools.sh gh-topics myorg/repo --sync cli,tool   # Ensure topics exist

# Archive inactive repositories
./devtools.sh gh-archive -o myorg --inactive 365 --dry-run
./devtools.sh gh-archive -o myorg --empty            # Archive empty repos
./devtools.sh gh-archive myorg/old-repo              # Archive single repo

# Trigger GitHub Actions
./devtools.sh gh-workflow myorg/repo --list          # List workflows
./devtools.sh gh-workflow myorg/repo ci.yml          # Trigger workflow
./devtools.sh gh-workflow myorg/repo deploy.yml -i env=prod --wait
```

### Inside the Container

**Shell Scripts:**
- `git-stats.sh` - Comprehensive repository statistics
- `git-cleanup.sh` - Clean up merged/stale branches
- `git-lfs-migrate.sh` - LFS migration with 100+ file patterns
- `git-history-clean.sh` - Remove large files from history
- `git-branch-rename.sh` - Rename branches with remote sync
- `gh-create-repo.sh` - Create GitHub repositories
- `gh-trigger-workflow.sh` - Trigger GitHub Actions
- `help-devtools` - Show all available commands

**Python Tools:**
- `git-changelog.py` - Generate changelog from commits
- `git-release.py` - Semantic versioning release manager
- `git-split-repo.py` - Split monorepo into separate repos
- `git-rewrite-commits.py` - Pattern-based commit message rewriting
- `gh-topic-manager.py` - Manage repository topics
- `gh-archive-repos.py` - Archive repositories by criteria

**Pre-configured Git Aliases:**
| Alias | Command |
|-------|---------|
| `git st` | `status -sb` |
| `git lg` | Log graph (20 commits) |
| `git lga` | Full log graph, all branches |
| `git branches` | List branches by date |
| `git last` | Show last commit |
| `git undo` | Soft reset last commit |
| `git amend` | Amend last commit |

### Examples

```bash
# Repository statistics
./devtools.sh stats

# Clean up branches (preview)
./devtools.sh cleanup --dry-run

# Generate changelog
./devtools.sh run "git-changelog.py -o CHANGELOG.md"

# Interactive release
./devtools.sh release release

# Migrate to LFS
./devtools.sh lfs-migrate --dry-run
./devtools.sh lfs-migrate --push
```

---

## Dozzle - Container Monitor

Independent Docker container log viewer. See [services/dozzle/README.md](services/dozzle/README.md) for details.

### Quick Start

```bash
cd services/dozzle
cp .env.example .env
./scripts/dozzle.sh start
```

---

## Project Structure

```
DeveloperTools/
├── devtools.sh              # DevTools CLI (Linux/macOS)
├── devtools.ps1             # DevTools CLI (Windows)
│
├── services/
│   ├── devtools/            # DevTools Runtime Container
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   ├── requirements.txt
│   │   └── scripts/
│   │       ├── git-stats.sh
│   │       ├── git-cleanup.sh
│   │       ├── git-changelog.py
│   │       ├── git-release.py
│   │       ├── git-lfs-migrate.sh
│   │       ├── git-history-clean.sh
│   │       ├── git-branch-rename.sh
│   │       ├── git-split-repo.py
│   │       ├── git-rewrite-commits.py
│   │       ├── gh-create-repo.sh
│   │       ├── gh-topic-manager.py
│   │       ├── gh-archive-repos.py
│   │       ├── gh-trigger-workflow.sh
│   │       └── help-devtools
│   │
│   └── dozzle/              # Container Monitor (independent)
│       ├── docker-compose.yml
│       ├── .env.example
│       ├── README.md
│       ├── data/
│       │   └── users.yml.example
│       └── scripts/
│           ├── dozzle.sh
│           └── dozzle.ps1
│
└── .github/                 # CI/CD workflows
```

## Adding New Tools

1. Add scripts to `services/devtools/scripts/`
2. Make them executable in the Dockerfile
3. Add Python dependencies to `requirements.txt`
4. Update `help-devtools` with new commands
5. Add CLI integration to `devtools.sh` and `devtools.ps1`

## Requirements

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose v2+ (for Dozzle)
- GitHub CLI (`gh`) for GitHub tools (installed in container)

## License

MIT
