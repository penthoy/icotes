# Docker Missing Dependencies - Root Cause Analysis

**Date:** 2025-01-08  
**Branch:** 41-multimedia-support-and-hop-integration  
**Status:** Root cause identified

---

## Executive Summary

The Docker container fails where dev server succeeds because **the Dockerfile only installs `requirements.txt` but ignores `pyproject.toml` dependencies**. In development, `uv` reads `pyproject.toml` and installs all agentic/hop dependencies automatically. In Docker, these critical packages are missing.

---

## The Smoking Gun

### What's Missing in Docker

```dockerfile
# Dockerfile lines 40-51
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir python-jose[cryptography]
```

**Problem:** Only `requirements.txt` is installed. No `pyproject.toml` dependencies.

### What Dev Has That Docker Doesn't

**From `pyproject.toml` (NOT in `requirements.txt`):**
- ✅ `google-generativeai>=0.8.0` - **Required by `imagen_tool.py`**
- ✅ `asyncssh>=2.14.2` - **Required by `hop_service.py`**
- ✅ `python-dotenv>=0.21.0` - **Required by all agents**
- ✅ `openai-agents>=0.0.6` - **Required by OpenAI agent framework**
- ✅ All agentic framework packages (openai, crewai, langchain, etc.)

### Evidence

**1. OpenAI Agent Import Error:**
```python
# backend/icpy/agent/agents/openai_agent.py:44
from icpy.agent.clients import get_openai_client  # Works in dev
from icpy.agent.helpers import (...)  # Works in dev

# backend/icpy/agent/clients.py:2
from openai import OpenAI  # ✅ IN requirements.txt
from dotenv import load_dotenv  # ❌ ONLY in pyproject.toml
```

**2. Imagen Tool Import:**
```python
# backend/icpy/agent/tools/imagen_tool.py:23
import google.generativeai as genai  # ❌ ONLY in pyproject.toml
```

**3. SSH Hop Service:**
```python
# backend/icpy/services/hop_service.py:29
import asyncssh  # ❌ ONLY in pyproject.toml
```

---

## Why Dev Works But Docker Doesn't

### Development Environment
```bash
# When you run: uv run python ...
# Or: uv sync
uv reads pyproject.toml → installs ALL dependencies → everything works
```

### Docker Container
```bash
# When Docker builds:
pip install -r requirements.txt → ONLY installs requirements.txt → missing packages
```

### The Disconnect

| Package | requirements.txt | pyproject.toml | Docker Has It? | Dev Has It? |
|---------|-----------------|----------------|----------------|-------------|
| `openai` | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| `fastapi` | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| `python-dotenv` | ❌ No | ✅ Yes | ❌ **NO** | ✅ Yes |
| `google-generativeai` | ❌ No | ✅ Yes | ❌ **NO** | ✅ Yes |
| `asyncssh` | ❌ No | ✅ Yes | ❌ **NO** | ✅ Yes |
| `openai-agents` | ❌ No | ✅ Yes | ❌ **NO** | ✅ Yes |

---

## Impact on Reported Issues

### 1. OpenAI Agent Failure
**Symptom:** "OpenAIAgent dependencies are not available"

**Root Cause:** `python-dotenv` missing in Docker
- Agent tries: `from dotenv import load_dotenv`
- Import fails → `DEPENDENCIES_AVAILABLE = False`
- Returns error message to user

### 2. SSH Hop Connection Failure
**Symptom:** Connection shows "disconnected" immediately after connect

**Root Cause:** `asyncssh` missing in Docker
- `hop_service.py` tries: `import asyncssh`
- Import likely fails silently or connection objects not created properly
- Connection stored as `None` → status check returns "disconnected"
- `lastConnectedAt: null` confirms connection never established

### 3. Image Generation Widget Issues
**Symptom:** Various failures with image generation

**Root Cause:** `google-generativeai` and/or `Pillow` issues
- `Pillow` IS in requirements.txt, but may have version conflicts
- `google-generativeai` NOT in requirements.txt at all

---

## Why This Wasn't Obvious

1. **Silent Import Failures**
   - Python imports wrapped in try/except blocks
   - Errors logged but app continues running
   - No startup failure, just runtime errors

2. **Two Sources of Truth**
   - `requirements.txt` - Old, possibly outdated
   - `pyproject.toml` - Current, actively maintained
   - Docker uses old source, dev uses new source

3. **Different Package Managers**
   - Docker: `pip` (reads requirements.txt)
   - Dev: `uv` (reads pyproject.toml)
   - Both work independently, creating version skew

4. **Error Messages Were Misleading**
   - "Dependencies not available" suggested missing packages
   - But which packages? No specifics in Docker logs
   - Dev worked fine, so seemed like Docker environment issue

---

## The Fix

### Option 1: Install from pyproject.toml (Recommended)

```dockerfile
# Replace lines 46-51 in Dockerfile with:
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir -e .
```

**Pros:**
- Single source of truth
- Always in sync
- Future-proof

**Cons:**
- Slower build (installs dev dependencies too)

### Option 2: Sync requirements.txt with pyproject.toml

```bash
# Generate requirements.txt from pyproject.toml
cd backend
uv pip compile pyproject.toml -o requirements.txt
```

**Pros:**
- Keeps current Docker build pattern
- Faster builds (explicit dependencies only)

**Cons:**
- Must regenerate when pyproject.toml changes
- Easy to forget and drift out of sync

### Option 3: Install Both

```dockerfile
# In Dockerfile, add:
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -e .  # Install pyproject.toml extras
```

**Pros:**
- Ensures nothing missing
- Minimal Dockerfile changes

**Cons:**
- Redundant installations
- Larger image size
- Potential version conflicts

---

## Recommended Solution

**Use Option 1:** Install from `pyproject.toml` exclusively.

### Updated Dockerfile (lines 40-51)

```dockerfile
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

# Copy Python dependency file
COPY backend/pyproject.toml ./

# Install Python dependencies from pyproject.toml (single source of truth)
RUN pip install --no-cache-dir -e .
```

### Why This Works

1. **Single Source of Truth** - All dependencies in one place
2. **Matches Dev Environment** - Both use pyproject.toml
3. **Future-Proof** - New dependencies automatically included
4. **Eliminates Drift** - Can't forget to update requirements.txt

---

## Testing the Fix

### 1. Rebuild Docker with Fix
```bash
cd ~/icotes/build
sudo ./cleanup_docker_images.sh -y
sudo ./build-docker.sh 2.0.1
```

### 2. Verify OpenAI Agent
```bash
# In Docker container, test:
docker exec -it icotes-web python -c "
from dotenv import load_dotenv
import google.generativeai as genai
import asyncssh
print('All imports successful!')
"
```

### 3. Test SSH Hop Connection
- Connect to SSH hop in UI
- Should stay "connected" instead of immediate "disconnected"
- `lastConnectedAt` should have a timestamp

### 4. Test OpenAI Agent
- Try image generation: "create a red circle with 128x128 pixels"
- Should work without "dependencies not available" error

---

## Lessons Learned

### For Future Development

1. **Always use pyproject.toml** as single source of truth
2. **Deprecate requirements.txt** or auto-generate it
3. **Test in Docker early** during feature development
4. **Add startup checks** for critical imports
5. **Log missing dependencies explicitly** with package names

### For Debugging

1. **Compare package lists** between environments first
2. **Check import statements** in failing modules
3. **Don't assume Docker == Dev** - they can diverge
4. **Look for silent failures** in try/except blocks
5. **Verify package manager behavior** (pip vs uv vs poetry)

---

## Files to Update

### 1. Dockerfile
- Line 46-51: Use pyproject.toml instead of requirements.txt

### 2. requirements.txt (Optional)
- Add comment: "DEPRECATED: Use pyproject.toml instead"
- Or delete entirely after Docker fix verified

### 3. build-docker.sh
- No changes needed

### 4. Documentation
- Update DOCKER_WORKFLOW_SETUP.md
- Note dependency management approach

---

## Verification Checklist

- [ ] Docker builds successfully with pyproject.toml
- [ ] OpenAI Agent works in Docker (no import errors)
- [ ] SSH Hop connects and stays connected
- [ ] Image generation works
- [ ] All agent tools accessible
- [ ] No new import errors in logs
- [ ] Image size reasonable (< 2GB)

---

## Summary

**Root Cause:** Dockerfile installs `requirements.txt` while dev uses `pyproject.toml`, causing missing dependencies in Docker.

**Key Missing Packages:**
- `python-dotenv` → OpenAI agent fails
- `asyncssh` → SSH hop fails
- `google-generativeai` → Image generation fails

**Fix:** Install from `pyproject.toml` in Dockerfile (single source of truth).

**Complexity:** Simple - One Dockerfile change, 5-minute rebuild.

---

## Next Steps

1. Apply Dockerfile fix (Option 1 above)
2. Rebuild Docker image
3. Test all three failing features
4. Remove diagnostic logging if features work
5. Commit fix with clear message
6. Update documentation
