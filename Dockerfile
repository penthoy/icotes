# Multi-stage Dockerfile for iCotes
# Build arguments for metadata
ARG BUILD_VERSION=1.0.3
ARG BUILD_DATE
ARG GIT_COMMIT

# Stage 1: Build frontend
FROM oven/bun:1.3.7-alpine AS frontend-builder

WORKDIR /app

# Copy package files first for better caching
COPY package.json bun.lock ./

# Install JS dependencies (including devDependencies for build)
RUN bun install --frozen-lockfile

# Copy frontend source code
COPY . .

# Build the frontend with dynamic configuration (no hardcoded URLs)
# Clear any local environment variables that might interfere
ENV VITE_API_URL=
ENV VITE_WS_URL=
ENV VITE_BACKEND_URL=
RUN bun run build

# Stage 2: Setup Python backend dependencies
FROM python:3.12-slim AS backend-base

# Optional Python feature sets (pyproject extras), comma separated, or "all".
# Default is a lean install with only the core dependencies. Examples:
#   --build-arg INSTALL_EXTRAS=documents,media
#   --build-arg INSTALL_EXTRAS=all
# Available extras: documents, media, discord, google, agents-frameworks, providers-sdk
# ("all" together with other extras means all.)
ARG INSTALL_EXTRAS=""

# Build tools are only needed here (compiling wheels); they are not copied to the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (build stage only)
RUN pip install --no-cache-dir uv

# Copy mode avoids hardlinks into a cache that is not kept; no cache keeps the layer small
ENV UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app/backend

# Copy uv dependency files (for better layer caching)
COPY backend/pyproject.toml backend/uv.lock ./

# Install production Python dependencies from lockfile (core + selected extras)
RUN set -eu; \
    extra_args=""; \
    for extra in $(printf '%s' "${INSTALL_EXTRAS}" | tr ',' ' ' | tr '[:upper:]' '[:lower:]'); do \
        if [ "${extra}" = "all" ]; then \
            extra_args="--all-extras"; \
            break; \
        fi; \
        extra_args="${extra_args} --extra ${extra}"; \
    done; \
    uv sync --frozen --no-dev --no-install-project ${extra_args}; \
    find /app/backend/.venv -type d -name __pycache__ -prune -exec rm -rf {} +

# Stage 3: Final production image
FROM python:3.12-slim

# Add build metadata as labels
ARG BUILD_VERSION
ARG BUILD_DATE
ARG GIT_COMMIT
LABEL version="${BUILD_VERSION}" \
      build_date="${BUILD_DATE}" \
      git_commit="${GIT_COMMIT}" \
      org.opencontainers.image.title="iCotes" \
      org.opencontainers.image.description="Interactive Code Execution and Terminal Environment" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.vendor="penthoy" \
      org.opencontainers.image.url="https://github.com/penthoy/icotes"

# Set ICOTES_DEV_TOOLS=1 (or true/yes) to also install developer conveniences in the image
# (sudo, editors, compilers, htop, locales, uv). The default image stays lean.
ARG ICOTES_DEV_TOOLS=0

# Runtime system dependencies:
#   tini (PID 1), procps (PTY/process support), bash (terminal), git (source control),
#   ripgrep (semantic search), curl + ca-certificates (healthcheck, HTTPS)
RUN case "$(printf '%s' "${ICOTES_DEV_TOOLS}" | tr '[:upper:]' '[:lower:]')" in 1|true|yes) dev_tools=1 ;; *) dev_tools=0 ;; esac \
    && apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tini procps bash git ripgrep \
    && if [ "${dev_tools}" = "1" ]; then \
        apt-get install -y --no-install-recommends \
            sudo bash-completion locales \
            vim nano htop less \
            build-essential make \
            unzip zip \
        && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
        && locale-gen \
        && pip install --no-cache-dir uv; \
    fi \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security (add early so we can configure)
RUN case "$(printf '%s' "${ICOTES_DEV_TOOLS}" | tr '[:upper:]' '[:lower:]')" in 1|true|yes) dev_tools=1 ;; *) dev_tools=0 ;; esac \
    && useradd --create-home --shell /bin/bash icotes \
    && if [ "${dev_tools}" = "1" ]; then \
        echo 'icotes ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/icotes \
        && chmod 440 /etc/sudoers.d/icotes; \
    fi

# Provide a friendly bash configuration (aliases, colors) for the web terminal
RUN cat <<'EOF' >> /home/icotes/.bashrc
# --- iCotes terminal conveniences ---
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export TERM=xterm-256color
# Color prompt if supported
if [ -n "$PS1" ]; then
  if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    PS1='\[\e[01;32m\]\u@\h \[\e[01;34m\]\w\[\e[00m\]$ '
  fi
fi
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'
# Load bash completion if available
if [ -f /etc/bash_completion ]; then
  . /etc/bash_completion
fi
# --- end ---
EOF
RUN chown icotes:icotes /home/icotes/.bashrc \
    && echo 'if [ -f ~/.bashrc ]; then . ~/.bashrc; fi' > /home/icotes/.bash_profile \
    && chown icotes:icotes /home/icotes/.bash_profile

USER icotes

WORKDIR /app

ARG AGENT_MAX_TOKENS=8000
ARG AGENT_AUTO_CONTINUE=1
ARG AGENT_MAX_CONTINUE_ROUNDS=10

# Copy backend source code
COPY --chown=icotes:icotes backend/ ./backend/

# Copy Python virtualenv from backend-base stage
COPY --from=backend-base --chown=icotes:icotes /app/backend/.venv /app/backend/.venv

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder --chown=icotes:icotes /app/dist ./dist/

# Create necessary directories
RUN mkdir -p ./logs ./workspace

# WORKSPACE FIX: Copy workspace files with sample content
COPY --chown=icotes:icotes workspace/ ./workspace/

# Set environment variables
ENV PORT=8000 \
    AUTH_MODE=standalone \
    NODE_ENV=production \
  VIRTUAL_ENV=/app/backend/.venv \
  PATH="/app/backend/.venv/bin:$PATH" \
    WORKSPACE_ROOT=/app/workspace \
    VITE_WORKSPACE_ROOT=/app/workspace \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TERM=xterm-256color \
    BUILD_VERSION=${BUILD_VERSION} \
    BUILD_DATE=${BUILD_DATE} \
    GIT_COMMIT=${GIT_COMMIT} \
    AGENT_MAX_TOKENS=${AGENT_MAX_TOKENS} \
    AGENT_AUTO_CONTINUE=${AGENT_AUTO_CONTINUE} \
    AGENT_MAX_CONTINUE_ROUNDS=${AGENT_MAX_CONTINUE_ROUNDS}

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Change to backend directory for proper imports
WORKDIR /app/backend

# TERMINAL FIX: Use privileged mode for PTY support
# Use tini as init system and start the application
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/backend/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "logging.conf"]
