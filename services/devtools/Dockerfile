# =============================================================================
# DevTools Runtime Container
# Git-focused development tools with Python support
# Plattformunabhängiger Container für Git-Operationen und Entwicklungstools
# =============================================================================

FROM python:3.23-alpine

LABEL maintainer="Bauer Group"
LABEL description="Swiss Army Knife for Git-based Development"
LABEL version="1.0.0"

# =============================================================================
# System Dependencies
# =============================================================================
RUN apk add --no-cache \
    # Core utilities
    bash \
    coreutils \
    grep \
    sed \
    findutils \
    # Git ecosystem
    git \
    git-lfs \
    git-fast-import \
    openssh-client \
    gnupg \
    # Security & Crypto
    openssl \
    ca-certificates \
    # Build tools (for Python packages)
    gcc \
    musl-dev \
    libffi-dev \
    # Network tools
    curl \
    wget \
    # JSON processing
    jq \
    yq \
    # Docker CLI (interact with host Docker)
    docker-cli \
    docker-cli-compose \
    # Editors
    nano \
    vim \
    # Extra utilities
    tree \
    less \
    ncurses

# =============================================================================
# Python Dependencies
# =============================================================================
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# =============================================================================
# Git Configuration
# =============================================================================
# Safe directory für gemountete Volumes
RUN git config --system --add safe.directory '*'

# Hilfreiche Git-Aliase
RUN git config --system alias.st 'status -sb' && \
    git config --system alias.lg 'log --oneline --graph --decorate -20' && \
    git config --system alias.lga 'log --oneline --graph --decorate --all -30' && \
    git config --system alias.co 'checkout' && \
    git config --system alias.br 'branch -vv' && \
    git config --system alias.ci 'commit' && \
    git config --system alias.df 'diff' && \
    git config --system alias.dfs 'diff --staged' && \
    git config --system alias.last 'log -1 HEAD --stat' && \
    git config --system alias.unstage 'reset HEAD --' && \
    git config --system alias.amend 'commit --amend --no-edit' && \
    git config --system alias.undo 'reset --soft HEAD~1' && \
    git config --system alias.stash-all 'stash save --include-untracked' && \
    git config --system alias.branches 'branch -a --sort=-committerdate' && \
    git config --system alias.tags 'tag -l --sort=-version:refname' && \
    git config --system alias.contributors 'shortlog -sn --all' && \
    git config --system alias.file-history 'log --follow -p --'

# =============================================================================
# Shell Configuration
# =============================================================================
SHELL ["/bin/bash", "-c"]

# Custom bash prompt with git branch
RUN echo 'parse_git_branch() { git branch 2>/dev/null | grep "^*" | sed "s/* //"; }' >> /etc/profile.d/devtools.sh && \
    echo 'export PS1="\[\033[1;34m\]devtools\[\033[0m\]:\[\033[1;32m\]\w\[\033[0m\] \[\033[1;33m\]\$(parse_git_branch)\[\033[0m\]\$ "' >> /etc/profile.d/devtools.sh && \
    echo 'export TERM=xterm-256color' >> /etc/profile.d/devtools.sh && \
    echo 'alias ll="ls -la --color=auto"' >> /etc/profile.d/devtools.sh && \
    echo 'alias la="ls -A --color=auto"' >> /etc/profile.d/devtools.sh && \
    echo 'alias l="ls -CF --color=auto"' >> /etc/profile.d/devtools.sh

# =============================================================================
# Scripts Directory
# =============================================================================
COPY scripts/ /opt/devtools/
RUN chmod +x /opt/devtools/*.sh /opt/devtools/*.py 2>/dev/null || true
ENV PATH="/opt/devtools:${PATH}"

# =============================================================================
# Working Directory
# =============================================================================
WORKDIR /workspace

# Entrypoint für Initialisierung
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash", "-l"]
