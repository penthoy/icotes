# Groq Multimodal Content Fix

**Date**: October 9, 2025  
**Issue**: Error code 400 - `messages[2].content must be a string`  
**Root Cause**: Groq API doesn't support OpenAI's rich content arrays for multimodal input

## Problem

When dragging images from Explorer into Chat with GroqKimiAgent selected, the backend was building OpenAI-style multimodal content:

```python
{
  "role": "user",
  "content": [
    {"type": "text", "text": "can you add a hat to it?"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]
}
```

**Groq's API requires plain strings**, not arrays. This caused:
```
Error code: 400 - {'error': {'message': 'messages[2].content must be a string', 'type': 'invalid_request_error'}}
```

## Solution

### 1. Convert Rich Content to Text with File Paths

Added `_extract_text_from_rich()` helper in `groq_kimi_agent.py` that:
- Extracts text parts from multimodal arrays
- Extracts file paths from `image_url` entries
- Converts `file://` URLs to plain paths
- Appends image context as text:
  ```
  can you add a hat to it?
  
  [Attached images:
  - /home/penthoy/icotes/workspace/dog_in_forest.png
  ]
  ```

### 2. Updated System Prompt

Modified GroqKimiAgent's system prompt to explain:
- User messages may include `[Attached images: ...]` sections
- Use the file paths with `generate_image` tool for editing
- Set `mode='edit'` when modifying attached images

### 3. Tool Integration

The agent can now:
1. See file paths in the message text
2. Call `generate_image` tool with:
   ```python
   {
     "prompt": "add a red hat",
     "image_data": "/home/penthoy/icotes/workspace/dog_in_forest.png",
     "mode": "edit"
   }
   ```
3. Edit the image using the file path

## Code Changes

**File**: `backend/icpy/agent/agents/groq_kimi_agent.py`

### Before
```python
# Preserved rich content arrays (caused 400 error on Groq)
if role == "user" and _is_rich_parts(c):
    safe_messages.append(m)  # Array format
```

### After
```python
# Convert to plain text with file path hints
if role == "user" and _is_rich_parts(c):
    text_content = _extract_text_from_rich(c)  # String format
    safe_messages.append({**m, "content": text_content})
```

## Testing

### Expected Behavior
1. Drag `workspace/dog_in_forest.png` to chat
2. Type: "can you add a red hat to it?"
3. Send with GroqKimiAgent selected

### Expected Logs
```
GroqKimiAgent: Prepared 3 messages (last user has image hints: True)
GroqKimiAgent: Starting chat with tools enabled (compact mode)
```

### Expected Result
- No 400 error
- Agent receives message with file path in text
- Agent can call `generate_image` tool to edit the image

## Why This Works

1. **API Compatibility**: Groq requires strings → we convert arrays to strings
2. **Tool Usage**: File paths in text → agent can use them with tools
3. **User Intent**: Image editing requests → agent knows which file to modify
4. **Graceful Degradation**: If no vision API, at least tools can access files

## Related Files

- `backend/icpy/agent/agents/groq_kimi_agent.py` - Main fix
- `backend/icpy/services/chat_service.py` - Builds multimodal content
- `backend/icpy/agent/tools/imagen_tool.py` - Handles image editing

## Alternative Approaches Considered

1. ❌ **Use vision-capable Groq models** - None available yet
2. ❌ **Embed as base64 in text** - Token limit issues
3. ✅ **Convert to text with file paths** - Works with existing tools
4. ❌ **Skip images entirely** - Loses user intent

## Future Improvements

- When Groq adds vision support, detect and use native multimodal format
- Add automatic model selection based on capabilities
- Cache image embeddings for faster tool access
