# OpenAIAgent Dependencies Regression - Quick Fix Guide

## Issue
OpenAIAgent showing "dependencies are not available" error in Docker container (see screenshot).

## Root Cause
**Most likely:** Stale Docker layer caching from previous builds. The `openai>=1.60.0` package may not have been properly installed due to cached layers.

## Quick Fix (Recommended)

### Step 1: Diagnose the Issue
Run the diagnostic script to confirm:
```bash
cd ~/icotes/build
chmod +x diagnose-agent-deps.sh
./diagnose-agent-deps.sh
```

This will check:
- ✅ If `openai` package is installed
- ✅ If import paths are correct
- ✅ If there are import errors in logs
- ✅ If `requirements.txt` has the dependencies

### Step 2: Rebuild with No Cache
The enhanced debug logging has been added to `openai_agent.py`. Now rebuild:

```bash
cd ~/icotes/build
sudo ./cleanup_docker_images.sh -y
sudo ./build-docker.sh 2.0.0 --no-cache
```

The `--no-cache` flag ensures fresh pip install from `requirements.txt`.

### Step 3: Verify the Fix
After rebuilding, check the backend logs:
```bash
docker logs -f <container_id> 2>&1 | grep -E '\[OpenAIAgent\]|Import error'
```

Expected output:
```
[OpenAIAgent] All dependencies available for OpenAIAgent
```

If you still see errors, the full traceback will now show the exact issue.

### Step 4: Test OpenAIAgent
Send a message to OpenAIAgent - should work without dependency error.

## What Changed

### Enhanced Debug Logging
**File:** `backend/icpy/agent/agents/openai_agent.py`

Added detailed error logging to diagnose import failures:
- Full traceback of import error
- System path contents
- ICOTES_BACKEND_PATH environment variable
- Exact error message

### Build Script Enhancement
**File:** `build/build-docker.sh`

Now supports `--no-cache` flag:
```bash
./build-docker.sh 2.0.0 --no-cache
```

### Diagnostic Script
**File:** `build/diagnose-agent-deps.sh`

New script to quickly diagnose dependency issues:
- Checks installed packages
- Tests imports
- Examines logs
- Verifies requirements.txt

## Why This Happens

Docker layer caching is aggressive during development:
1. You modify code frequently
2. Docker reuses the pip install layer if `requirements.txt` hasn't changed
3. But if packages failed to install previously, the cached layer is broken
4. `--no-cache` forces a fresh install

## Prevention

Always use `--no-cache` when:
- Dependencies have changed
- Previous build had errors
- Switching between branches with different dependencies
- After cleaning up Docker images

## Related Files Modified
- `backend/icpy/agent/agents/openai_agent.py` - Added debug logging
- `build/build-docker.sh` - Added --no-cache support
- `build/diagnose-agent-deps.sh` - New diagnostic script
- `docs/fixes/openai_agent_docker_dependencies.md` - Full documentation

## Next Steps

1. Run diagnostic script
2. Rebuild with --no-cache
3. Check logs for the enhanced error messages
4. If still failing, share the full traceback from logs

The enhanced logging will show exactly which import is failing and why.
