# Debugging Updates - Image Generation Issues

**Date**: October 10, 2025  
**Purpose**: Add comprehensive logging to debug SyntaxError and aspect ratio issues

## Changes Made

### 1. Fixed NanoBananaAgent Output Format

**Files**:
- `/backend/icpy/agent/agents/nano_banana_agent.py` (line 427)
- `/backend/icpy/agent/agents/openrouter_nano_banana_agent.py` (line 350)

**Change**: Remove decoration from JSON output
```python
# Before (causing SyntaxError)
yield f"✅ **Success**: {json.dumps(tool_call_output)}\n"

# After (pure JSON)
yield json.dumps(tool_call_output) + "\n"
```

**Why**: Frontend was trying to parse `"✅ **Success**: {...}"` as JSON, which failed

### 2. Added System Prompt Logging (GroqKimiAgent)

**File**: `/backend/icpy/agent/agents/groq_kimi_agent.py`

**Added** (after line 224):
```python
# Log the system prompt to verify aspect ratio instruction is present
system_msg = next((m for m in safe_messages if m.get('role') == 'system'), None)
if system_msg:
    logger.info(f"GroqKimiAgent: System prompt includes: {system_msg['content'][:500]}")
```

**Purpose**: Verify that aspect ratio instruction is actually in the prompt sent to the model

### 3. Added Tool Call Parameter Logging

**File**: `/backend/icpy/agent/helpers.py` (OpenAIStreamingHandler._handle_tool_calls)

**Added** (after line 870):
```python
# Debug logging for image generation tool calls
if tool_name == 'generate_image':
    logger.info(f"🎨 Image generation tool call - aspect_ratio: {arguments.get('aspect_ratio', 'NOT SET')}, "
              f"mode: {arguments.get('mode', 'NOT SET')}, image_data: {bool(arguments.get('image_data'))}")
```

**Purpose**: See exactly what parameters the agent is sending to the image generation tool

### 4. Enhanced ImagenTool Logging

**File**: `/backend/icpy/agent/tools/imagen_tool.py` (already updated in previous fix)

Logs all kwargs including:
- aspect_ratio
- mode
- image_data presence
- prompt preview

## How to Test

### Backend Reload Status
The backend is running with `--reload` flag from `npm run dev`, so changes should auto-reload.

**Verify reload worked**:
```bash
# Check if process is running
ps aux | grep "uvicorn main:app" | grep -v grep

# Watch logs for new entries
tail -f /home/penthoy/icotes/logs/backend.log
```

### Test Case: Generate New Image

**Command**: "create an image of a mountain"

**Expected logs**:
```
INFO:groq_kimi_agent: System prompt includes: You are GroqKimiAgent...default to aspect_ratio='1:1'...
INFO:icpy.agent.helpers: 🎨 Image generation tool call - aspect_ratio: 1:1, mode: generate, image_data: False
INFO:icpy.agent.tools.imagen_tool: === ImagenTool.execute START ===
INFO:icpy.agent.tools.imagen_tool:   aspect_ratio: 1:1
```

**If aspect_ratio is still NOT SET or 16:9**:
- The model is ignoring the system prompt instruction
- May need stronger prompt engineering or parameter forcing

### Test Case: Edit Existing Image

**Commands**:
1. "create an image of a dog"
2. "add a hat to it"

**Expected logs for second command**:
```
INFO:icpy.agent.helpers: 🎨 Image generation tool call - aspect_ratio: NOT SET, mode: edit, image_data: True
INFO:icpy.agent.tools.imagen_tool:   image_data value: file:///home/.../img_xxx.png
INFO:icpy.agent.tools.imagen_tool:   mode: edit
```

**If image_data is still a filename instead of file:// URL**:
- Check that sanitization is working correctly
- Verify imageUrl is in the tool result sent to LLM

## Log Locations

**Backend**: `/home/penthoy/icotes/logs/backend.log`
**Frontend**: `/home/penthoy/icotes/logs/frontend.log`

## Expected Log Patterns

### Successful Image Generation
```
INFO:icpy.agent.helpers: 🎨 Image generation tool call - aspect_ratio: 1:1, mode: generate, image_data: False
INFO:icpy.agent.tools.imagen_tool: === ImagenTool.execute START ===
INFO:icpy.agent.tools.imagen_tool:   kwargs: {'prompt': '...', 'aspect_ratio': '1:1', ...}
INFO:icpy.agent.tools.imagen_tool:   aspect_ratio: 1:1
INFO:icpy.agent.tools.imagen_tool: ImagenTool mode=generate prompt_len=50 model=gemini-2.5-flash-image-preview
```

### Successful Image Editing
```
INFO:icpy.agent.helpers: 🎨 Image generation tool call - aspect_ratio: NOT SET, mode: edit, image_data: True
INFO:icpy.agent.tools.imagen_tool:   image_data value: file:///home/.../img_xxx.png
INFO:icpy.agent.tools.imagen_tool:   mode: edit
```

### SyntaxError (should be gone now)
```
# OLD (should not appear anymore)
WARN: Failed to parse image generation output: SyntaxError: Unexpected token 'G', "Generated "...

# If still appearing, means:
# 1. Backend didn't reload
# 2. Different agent is being used
# 3. Need to check which agent is active
```

## Troubleshooting

### If SyntaxError persists:

1. **Verify which agent is being used**:
   ```bash
   grep "Agent:" /home/penthoy/icotes/logs/backend.log | tail -5
   ```

2. **Check if backend reloaded**:
   ```bash
   tail -50 /home/penthoy/icotes/logs/backend.log | grep "Application startup"
   ```

3. **Manually restart backend**:
   ```bash
   # Kill existing
   pkill -f "uvicorn main:app"
   
   # Restart via npm
   cd /home/penthoy/icotes && npm run dev
   ```

### If aspect_ratio still wrong:

1. **Check system prompt in logs**:
   ```bash
   grep "System prompt includes" /home/penthoy/icotes/logs/backend.log | tail -1
   ```
   Should contain: "default to aspect_ratio='1:1'"

2. **Check tool call parameters**:
   ```bash
   grep "🎨 Image generation tool call" /home/penthoy/icotes/logs/backend.log | tail -5
   ```

3. **If model ignores instruction**:
   - May need to use tool schema defaults instead of relying on prompt
   - Consider adding aspect_ratio default in tool definition
   - Or post-process tool calls to inject default if missing

## Next Steps

1. Test image generation in the UI
2. Monitor backend logs for the new debug output
3. Check if SyntaxError is resolved
4. Verify aspect_ratio parameters in logs
5. Report findings with log excerpts

## Files Modified

- `/backend/icpy/agent/agents/nano_banana_agent.py`
- `/backend/icpy/agent/agents/openrouter_nano_banana_agent.py`
- `/backend/icpy/agent/agents/groq_kimi_agent.py`
- `/backend/icpy/agent/helpers.py`
- `/backend/icpy/agent/tools/imagen_tool.py` (from previous fix)
