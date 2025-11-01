# Quick Test Guide: Image Drag-and-Drop to Chat

## Steps to Test

### 1. Restart Backend (pick up new logging)
```bash
# Stop current server (Ctrl+C in the start-dev.sh terminal)
# Then restart:
./start-dev.sh
```

### 2. Open Chat in Browser
- Navigate to: http://localhost:8000
- Open Chat panel (should auto-connect)

### 3. Drag Image from Explorer
- In Explorer panel, locate: `workspace/dog_in_forest.png`
- Drag the image into the chat composer area
- You should see a preview thumbnail appear

### 4. Send Message
- Type: "can you add a red hat to it?"
- Press Enter or click Send
- Select "GroqKimiAgent" from the dropdown if not already selected

### 5. Watch Logs
**In a separate terminal**, run:
```bash
tail -f logs/backend.log | grep -E "📨|📎|🤖|🔍|✅|❌|📝|📤|Custom agent"
```

## Expected Log Output (Success)

You should see a sequence like this:

```
📨 Received message with 1 raw attachments from metadata
📎 Normalized to 1 attachments
  - dog_in_forest.png (kind: images, abs_path: /home/penthoy/icotes/workspace/dog_in_forest.png, mime: image/png)
🤖 Processing message with custom agent: GroqKimiAgent
📎 User message has 1 attachments: [...]
🔍 Building multimodal content for 1 attachments
Custom agent: Processing 1 attachments
Custom agent: Processing attachment id=explorer-1759977377805-... kind=images mime=image/png ...
Custom agent: Attempting to embed explorer image from absolute path
Custom agent: Successfully embedded explorer image as data URL (length: ~500000)
✅ Successfully added image to content_parts (total images: 1)
📝 Final content_parts structure: 2 parts (text + 1 images)
✅ Appended multimodal message to history_list (total history: X messages)
📤 Sending to agent GroqKimiAgent with history of X messages
📤 Last message role: user, content type: <class 'list'>, has images: True
```

## What Each Log Tells Us

| Log Line | What It Means | If Missing |
|----------|--------------|------------|
| 📨 Received message | Frontend sent attachments | Check frontend sendPipeline |
| 📎 Normalized to 1 | Backend parsed attachments | Check _normalize_attachments |
| 🤖 Processing with custom agent | Agent routing works | Check agent selection |
| 🔍 Building multimodal | Starting image embed | Check try/except wrapper |
| Custom agent: Processing | Loop started | Check attachment list not empty |
| Attempting to embed | File access starting | Check WORKSPACE_ROOT |
| Successfully embedded | Image converted to base64 | Check file permissions/size |
| ✅ Successfully added | Image in content_parts | Check content_parts append |
| 📝 Final content_parts | Ready to send | Check history_list.append |
| ✅ Appended multimodal | In history now | Check for exceptions |
| 📤 Sending to agent | Final handoff | Check agent call |
| has images: True | Agent will receive images | Agent should see it now |

## Debugging Different Scenarios

### If logs stop at "📨 Received message"
**Issue**: Frontend not sending attachments or WebSocket issue  
**Check**: Browser console for errors, network tab for WebSocket frames

### If logs stop at "🔍 Building multimodal"
**Issue**: Exception during content building  
**Check**: Look for "❌ Failed to attach multimodal content" with error details

### If logs stop at "Attempting to embed"
**Issue**: File access failure  
**Check**: 
- `ls -la /home/penthoy/icotes/workspace/dog_in_forest.png`
- Echo `$WORKSPACE_ROOT` in backend environment

### If "Successfully embedded" never appears but no error
**Issue**: Silent failure in embedding logic  
**Check**: Image file size (>3MB by default triggers fallback)

### If agent still says "I don't see any image"
**Issue**: Agent not processing multimodal content correctly  
**Action**: We'll need to check the GroqKimiAgent implementation next

## Alternative Test: Check Chat History File

After sending, you can verify the message was stored correctly:

```bash
# Find the most recent session file
ls -lt workspace/.icotes/chat_history/session_*.jsonl | head -1

# Read the last user message
tail -2 workspace/.icotes/chat_history/session_*.jsonl | head -1 | jq '.attachments'
```

Should show:
```json
[{
  "id": "explorer-...",
  "filename": "dog_in_forest.png",
  "mime_type": "image/png",
  "absolute_path": "/home/penthoy/icotes/workspace/dog_in_forest.png",
  "kind": "images"
}]
```

## Success Criteria

✅ All log checkpoints appear in the expected sequence  
✅ No ❌ error logs  
✅ "has images: True" at the end  
✅ Agent generates a response that acknowledges the image

If all logs appear but agent still doesn't see image, the issue is in the GroqKimiAgent implementation, not the attachment flow.
