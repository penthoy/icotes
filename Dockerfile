# Multi-stage Dockerfile for iCotes
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install Node.js dependencies (including devDependencies for build)
RUN npm ci

# Copy frontend source code
COPY . .

# Build the frontend
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
RUN pip install uv

WORKDIR /app/backend

# Copy Python dependency files
COPY backend/requirements.txt ./

# Install Python dependencies with pip (fallback for complex dependencies)
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final production image
FROM python:3.12-slim

# Install system dependencies and tini for proper PID 1 handling
RUN apt-get update && apt-get install -y \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv in final image
RUN pip install --no-cache-dir uv

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash icotes
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

# Set environment variables
ENV PORT=8000
ENV AUTH_MODE=standalone
ENV NODE_ENV=production

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Change to backend directory for proper imports
WORKDIR /app/backend

# Use tini as init system and start the application
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
