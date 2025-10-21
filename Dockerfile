# Multi-stage Dockerfile for iCotes
# Build arguments for metadata
ARG BUILD_VERSION=1.0.3
ARG BUILD_DATE
ARG GIT_COMMIT

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install Node.js dependencies (including devDependencies for build)
RUN npm ci

# Copy frontend source code
COPY . .

# Build the frontend with dynamic configuration (no hardcoded URLs)
# Clear any local environment variables that might interfere
ENV VITE_API_URL=
ENV VITE_WS_URL=
ENV VITE_BACKEND_URL=
RUN npm run build

# Stage 2: Setup Python backend dependencies
FROM python:3.12-slim AS backend-base

# Install system dependencies including build tools for compiled packages
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

WORKDIR /app/backend

# Copy Python dependency files
COPY backend/requirements.txt ./

# Install base Python dependencies with pip (for C++ compatibility)
RUN pip install --no-cache-dir -r requirements.txt

# Install additional JWT dependency
RUN pip install --no-cache-dir python-jose[cryptography]

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

# Install system dependencies and tini for proper PID 1 handling
# CRITICAL FIX: Add procps for PTY support
# DEV-LIKE TOOLS: Add sudo, htop, git, editors, bash-completion, locales, build tools
# SEMANTIC SEARCH: Add ripgrep for semantic search functionality
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tini procps \
    sudo bash-completion locales \
    git vim nano htop less \
    build-essential gcc g++ make \
    unzip zip tar \
    ripgrep \
    && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv in final image
RUN pip install --no-cache-dir uv

# Create non-root user for security (add early so we can configure)
RUN useradd --create-home --shell /bin/bash icotes \
    && echo 'icotes ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/icotes \
    && chmod 440 /etc/sudoers.d/icotes

# Provide a developer-friendly bash configuration (aliases, colors)
RUN cat <<'EOF' >> /home/icotes/.bashrc
# --- iCotes dev conveniences ---
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
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

# Copy Python packages from backend-base stage
COPY --from=backend-base --chown=icotes:icotes /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-base --chown=icotes:icotes /usr/local/bin /usr/local/bin

# Copy backend source code
COPY --chown=icotes:icotes backend/ ./backend/

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
    WORKSPACE_ROOT=/app/workspace \
    VITE_WORKSPACE_ROOT=/app/workspace \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    TERM=xterm-256color \
    BUILD_VERSION=${BUILD_VERSION} \
    BUILD_DATE=${BUILD_DATE} \
    GIT_COMMIT=${GIT_COMMIT} \
    AGENT_MAX_TOKENS=8000 \
    AGENT_AUTO_CONTINUE=1 \
    AGENT_MAX_CONTINUE_ROUNDS=10

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
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "logging.conf"]
