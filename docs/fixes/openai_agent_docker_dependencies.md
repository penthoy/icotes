# OpenAIAgent Dependencies Issue in Docker

## Problem
OpenAIAgent showing "dependencies are not available" error in Docker container, but works in local development environment.

## Root Cause Analysis

The error message appears when the `try-except ImportError` block in `openai_agent.py` catches an import failure. Possible causes:

1. **Missing OpenAI package** - The `openai>=1.60.0` package might not be installed
2. **Import path issues** - The backend path resolution might fail in Docker
3. **Python package cache** - Docker layer caching might have stale packages
4. **Environment variables** - Missing or incorrect `ICOTES_BACKEND_PATH`

## Verification Steps

### 1. Check if OpenAI is Installed in Docker
```bash
docker exec -it <container_id> pip list | grep openai
```

Expected: `openai` package should appear with version >= 1.60.0

### 2. Check Backend Import Path
```bash
docker exec -it <container_id> python -c "import sys; import os; print(sys.path); print(os.environ.get('ICOTES_BACKEND_PATH'))"
```

### 3. Test Direct Import
```bash
docker exec -it <container_id> python -c "from icpy.agent.clients import get_openai_client; print('Success')"
```

### 4. Check Backend Logs
```bash
docker logs <container_id> 2>&1 | grep -i "openai\|import error"
```

## Solution

### Option 1: Force Clean Rebuild (Recommended)
The issue is likely stale Docker layer caching during dependency installation:

```bash
cd ~/icotes/build
sudo ./cleanup_docker_images.sh -y
sudo docker build --no-cache -t icotes:2.0.0 -f ../Dockerfile ..
```

### Option 2: Verify requirements.txt Has openai
Check that `backend/requirements.txt` includes:
```
openai>=1.60.0
```

If missing, the Dockerfile copies and installs this file at line 60:
```dockerfile
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

### Option 3: Add Debug Logging
Temporarily add debug output to see the exact import error:

**File:** `backend/icpy/agent/agents/openai_agent.py`

```python
except ImportError as e:
    import traceback
    logger.error(f"Import error in OpenAIAgent: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    DEPENDENCIES_AVAILABLE = False
```

Then rebuild and check logs:
```bash
docker logs <container_id> 2>&1 | grep -A 10 "Import error in OpenAIAgent"
```

## Implementation Plan

1. **Clean rebuild with no cache** (most likely fix)
2. **Verify in container**:
   ```bash
   docker exec -it <container_id> bash
   pip list | grep openai
   python -c "from icpy.agent.clients import get_openai_client; print(get_openai_client())"
   ```
3. **Test OpenAIAgent**:
   - Try sending a message to OpenAIAgent
   - Should work without dependency error

## Prevention

Add a health check endpoint that verifies agent dependencies:

**File:** `backend/main.py`

```python
@app.get("/api/agents/health")
async def check_agent_health():
    """Check if agent dependencies are available"""
    health = {}
    
    try:
        from icpy.agent.clients import get_openai_client
        get_openai_client()
        health['openai'] = 'ok'
    except Exception as e:
        health['openai'] = str(e)
    
    # Add other agents...
    
    return health
```

## Related Files
- `backend/requirements.txt` - Python dependencies
- `Dockerfile` - Multi-stage build with pip install
- `backend/icpy/agent/agents/openai_agent.py` - Agent implementation
- `backend/icpy/agent/clients.py` - OpenAI client factory

## Notes
- The same issue likely affects other agents (OllamaAgent, OpenRouterAgent, etc.)
- All agents use the same try-except pattern for dependency checking
- Docker layer caching can cause stale dependencies during rapid iteration
- The `--no-cache` flag ensures fresh pip install from requirements.txt
