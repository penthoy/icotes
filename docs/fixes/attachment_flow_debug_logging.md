# Attachment Flow Debug Logging Enhancement

**Date**: October 9, 2025  
**Issue**: Agent not receiving dragged images despite attachments being present in composer and stored in chat history  
**Status**: Debugging in progress

## Problem Analysis

From the screenshot and logs, we observed:
1. ✅ Image successfully dragged from Explorer into chat composer (preview visible)
2. ✅ Attachment data stored in JSONL chat history file with correct absolute path
3. ❌ Agent responds "I don't see any previous image" - attachments not reaching the agent

Example from session log:
```json
{
  "attachments": [{
    "id": "explorer-1759977377805-wle2xc3cc39",
    "filename": "dog_in_forest.png",
    "mime_type": "image/png",
    "absolute_path": "/home/penthoy/icotes/workspace/dog_in_forest.png",
    "kind": "images"
  }]
}
```

## Enhanced Logging Points

Added comprehensive logging at each critical step:

### 1. Message Reception (`handle_user_message`)
- **Log**: Number of raw attachments received from WebSocket
- **Log**: Number of attachments after normalization
- **Log**: Details of each normalized attachment (filename, kind, paths, mime type)

```python
logger.info(f"📨 Received message with {len(raw_attachments)} raw attachments from metadata")
logger.info(f"📎 Normalized to {len(attachments)} attachments")
for att in attachments:
    logger.info(f"  - {att.get('filename')} (kind: {att.get('kind')}, abs_path: {att.get('absolute_path')}, mime: {att.get('mime_type')})")
```

### 2. Custom Agent Processing (`_process_with_custom_agent`)
- **Log**: Agent type and attachment count at entry
- **Log**: Start of multimodal content building
- **Log**: Each attachment being processed with full details
- **Log**: Success/failure of image embedding
- **Log**: Final content_parts structure
- **Log**: Confirmation of history list update

```python
logger.info(f"🤖 Processing message with custom agent: {agent_type}")
logger.info(f"📎 User message has {len(user_message.attachments)} attachments")
logger.info(f"🔍 Building multimodal content for {len(user_message.attachments)} attachments")
logger.info(f"✅ Successfully added image to content_parts (total images: {added_images})")
logger.info(f"📝 Final content_parts structure: {len(content_parts)} parts")
logger.info(f"✅ Appended multimodal message to history_list")
```

### 3. Image Embedding Process
- **Log**: Attempt to embed from absolute path
- **Log**: WORKSPACE_ROOT validation
- **Log**: File size check
- **Log**: Success with data URL length
- **Error Log**: Any failures with full exception info

```python
logger.info(f"Custom agent: Attempting to embed explorer image from absolute path")
logger.info(f"Custom agent: Successfully embedded explorer image as data URL (length: {len(data_url)})")
logger.error(f"❌ Failed to process attachment: {embed_error}", exc_info=True)
```

### 4. Agent Invocation
- **Log**: Final history structure before sending to agent
- **Log**: Last message content type and image presence check

```python
logger.info(f"📤 Sending to agent {agent_type} with history of {len(history_list)} messages")
logger.info(f"📤 Last message has images: {has_images}")
```

## Log Symbols Reference

| Symbol | Meaning |
|--------|---------|
| 📨 | Message received from WebSocket |
| 📎 | Attachment processing |
| 🤖 | Agent selection/routing |
| 🔍 | Detailed inspection/building |
| ✅ | Success operation |
| ❌ | Failed operation |
| 📝 | Data structure logging |
| 📤 | Data being sent to agent |

## Expected Log Sequence (Success Case)

For a successful image drag-and-drop flow, we should see:

```
📨 Received message with 1 raw attachments from metadata
📎 Normalized to 1 attachments
  - dog_in_forest.png (kind: images, abs_path: /home/penthoy/icotes/workspace/dog_in_forest.png, mime: image/png)
🤖 Processing message with custom agent: GroqKimiAgent
📎 User message has 1 attachments: [...]
🔍 Building multimodal content for 1 attachments
Custom agent: Processing 1 attachments
Custom agent: Processing attachment id=explorer-... kind=images mime=image/png abs=/home/penthoy/.../dog_in_forest.png
Custom agent: Attempting to embed explorer image from absolute path
Custom agent: Successfully embedded explorer image as data URL (length: 12345)
✅ Successfully added image to content_parts (total images: 1)
📝 Final content_parts structure: 2 parts (text + 1 images)
✅ Appended multimodal message to history_list (total history: 3 messages)
📤 Sending to agent GroqKimiAgent with history of 3 messages
📤 Last message role: user, content type: <class 'list'>, has images: True
```

## Next Steps for Testing

1. **Restart the backend** to load new logging:
   ```bash
   # Kill existing process and restart
   ./start-dev.sh
   ```

2. **Test the flow**:
   - Drag `workspace/dog_in_forest.png` into chat
   - Type: "can you add a hat to it?"
   - Send the message

3. **Check logs**:
   ```bash
   tail -f logs/backend.log | grep -E "📨|📎|🤖|🔍|✅|❌|📝|📤"
   ```

4. **Analyze the output**:
   - If all symbols appear in sequence → Attachments reaching agent (investigate agent code)
   - If sequence breaks → Identify the exact failure point
   - Missing "Successfully embedded" → File access or permission issue
   - Missing "Appended multimodal" → Exception in content building

## Environment Verification

Key environment variables that must be set:
```bash
export WORKSPACE_ROOT=/home/penthoy/icotes/workspace
export CHAT_MAX_IMAGE_SIZE_MB=10  # Optional: increase if images are large
```

Verify with:
```bash
echo $WORKSPACE_ROOT
ls -lh $WORKSPACE_ROOT/dog_in_forest.png
```

## Common Failure Scenarios

### Scenario 1: "WORKSPACE_ROOT not set"
**Log**: `PermissionError: WORKSPACE_ROOT not set`  
**Fix**: Set environment variable in `.env` file

### Scenario 2: Image too large
**Log**: `ValueError: image_too_large`  
**Fix**: Increase `CHAT_MAX_IMAGE_SIZE_MB` or use smaller test image

### Scenario 3: File not found
**Log**: `FileNotFoundError: Invalid path`  
**Fix**: Verify file exists and path is correct

### Scenario 4: Path outside workspace
**Log**: Fails at `abs_path.relative_to(ws_root_p)`  
**Fix**: Ensure file is within WORKSPACE_ROOT

## Related Files

- `backend/icpy/services/chat_service.py`: Main attachment flow
- `src/icui/components/panels/ICUIChat.tsx`: Frontend composer
- `src/icui/components/chat/utils/sendPipeline.ts`: Attachment building
- `workspace/.icotes/chat_history/*.jsonl`: Stored messages

## Success Criteria

✅ All log checkpoints appear in sequence  
✅ "Successfully embedded explorer image as data URL" message present  
✅ "Appended multimodal message to history_list" confirmation  
✅ Agent receives and processes the image (generates response referencing the image)
