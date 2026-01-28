# Environment Configuration Guide

## Environment Files Overview

This project uses multiple environment files for different deployment scenarios:

### 📁 Environment Files

| File | Purpose | Usage |
|------|---------|-------|
| `.env` | **Local Development** | Used when running locally with `bun run dev` or `python main.py` |
| `.env.example` | **Template** | Copy this to `.env` for local development |
| `.env.production` | **Production Template** | Reference for production environment variables |

### 🐳 Docker Deployment

**Important**: Docker containers do NOT automatically use `.env` files. 

#### Default Docker Settings:
- `AGENT_MAX_TOKENS=8000` (set in Dockerfile)
- `AGENT_AUTO_CONTINUE=1`
- `AGENT_MAX_CONTINUE_ROUNDS=10`

#### Override via Environment Variables:
```bash
# For standalone deployment
docker run -p 8000:8000 \
  -e AGENT_MAX_TOKENS=10000 \
  -e AGENT_AUTO_CONTINUE=1 \
  penthoy/icotes:latest

# For docker-compose
# Edit docker-compose.yml environment section
```

### 🔧 Token Limit Configuration

The `AGENT_MAX_TOKENS` setting controls the maximum tokens per response chunk:

- **3500**: Conservative (old default)
- **8000**: Recommended for most use cases (new default)
- **10000+**: For complex tasks requiring longer responses

### 📝 Environment File Consolidation

To avoid confusion, we recommend:

1. **Development**: Use `.env` (copy from `.env.example`)
2. **Production**: Set environment variables directly in your deployment platform
3. **Docker**: Use the built-in defaults or override via `-e` flags

### 🚀 Quick Setup

For local development:
```bash
cp .env.example .env
# Edit .env with your API keys and preferences
bun run dev
```

For Docker deployment:
```bash
docker run -p 8000:8000 penthoy/icotes:latest
# Token limit is automatically set to 8000
```