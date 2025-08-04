# Stream Phased Debug: Custom Agent Streaming Issue

## Executive Summary

**Issue**: Custom agent responses appear as complete messages (`type: 'message'`) instead of streaming chunks (`type: 'message_stream'`) despite having a fully correct streaming implementation.

**Status**: ✅ Implementation is 100% correct and matches working main branch pattern. ❌ Execution/runtime issue preventing streaming protocol activation.

**Root Cause**: Backend is sending complete messages instead of executing the three-phase streaming protocol for custom agents.

## Findings Summary

### ✅ **What's Working Correctly**

1. **Frontend Implementation**: Perfect match with documented streaming pattern
   - Three-phase protocol handling (`stream_start`, `stream_chunk`, `stream_end`)
   - Duplicate prevention with `processedMessageIds`
   - Single streaming message accumulation
   - ID-based React state updates
   - No throttling/batching

2. **Backend Streaming Protocol**: Correctly implemented
   - `_send_streaming_start()`, `_send_streaming_chunk()`, `_send_streaming_end()`
   - Proper message structure with all required fields
   - Boolean phase flags correctly set
   - Message ID consistency across phases

3. **Custom Agent Integration**: Properly structured
   - OpenAI real streaming with `stream=True`
   - Chunk-by-chunk yielding pattern
   - Async generator implementation
   - Error handling with streaming fallback

### ❌ **What's Not Working**

**Critical Evidence**: Frontend logs show `type: 'message'` instead of `type: 'message_stream'`
```javascript
// Expected (streaming):
{type: 'message_stream', stream_start: true, id: '...', ...}
{type: 'message_stream', stream_chunk: true, chunk: 'Hello', id: '...', ...}
{type: 'message_stream', stream_end: true, id: '...', ...}

// Actual (complete message):
{type: 'message', content: 'Echo: what model are you?...', sender: 'ai', ...}
```

This indicates the backend is bypassing the streaming protocol entirely.

## Phase-by-Phase Debug Plan

### **Phase 1: Backend Streaming Activation Verification**

**Objective**: Confirm if `_process_with_custom_agent` is being called and executing the streaming loop.

**Debug Actions**:

1. **Add Entry Point Logging**
   ```python
   # In chat_service.py -> _process_with_custom_agent()
   logger.info(f"🎯 [DEBUG] _process_with_custom_agent CALLED for {agent_type}")
   logger.info(f"🎯 [DEBUG] Starting streaming loop for message: {user_message.content[:50]}")
   ```

2. **Add Streaming Loop Logging**
   ```python
   # In the async for loop
   async for chunk in custom_stream:
       logger.info(f"🎯 [DEBUG] Received chunk: '{chunk[:20]}...' (len={len(chunk)})")
       if chunk:
           if is_first_chunk:
               logger.info(f"🎯 [DEBUG] Sending STREAM_START")
               # ... existing code
           logger.info(f"🎯 [DEBUG] Sending STREAM_CHUNK: '{chunk[:20]}...'")
           # ... existing code
   ```

3. **Add Stream End Logging**
   ```python
   logger.info(f"🎯 [DEBUG] Sending STREAM_END. Total content: {len(full_content)} chars")
   ```

**Expected Results**:
- ✅ If logs appear: Streaming method is executing → **Proceed to Phase 2**
- ❌ If no logs: Method not being called → **Go to Phase 4 (Routing Debug)**

### **Phase 2: Custom Agent Stream Output Verification**

**Objective**: Verify that the custom agent is actually yielding chunks vs complete responses.

**Debug Actions**:

1. **Add Custom Agent Stream Logging**
   ```python
   # In custom_agent.py -> call_custom_agent_stream()
   logger.info(f"🔧 [DEBUG] Custom agent {agent_name} starting stream")
   chunk_count = 0
   
   for chunk in chat_function(message, history):
       chunk_count += 1
       logger.info(f"🔧 [DEBUG] Chunk {chunk_count}: '{chunk[:30]}...' (len={len(chunk)})")
       yield chunk
   
   logger.info(f"🔧 [DEBUG] Stream complete. Total chunks: {chunk_count}")
   ```

2. **Add OpenAI Agent Stream Logging**
   ```python
   # In openai_agent.py -> chat()
   chunk_count = 0
   for chunk in stream:
       if chunk.choices[0].delta.content is not None:
           chunk_count += 1
           content = chunk.choices[0].delta.content
           logger.info(f"🤖 [DEBUG] OpenAI chunk {chunk_count}: '{content[:20]}...'")
           yield content
   
   logger.info(f"🤖 [DEBUG] OpenAI stream complete. Total chunks: {chunk_count}")
   ```

**Expected Results**:
- ✅ Multiple small chunks: Agent streaming correctly → **Proceed to Phase 3**
- ❌ Single large chunk: Agent not streaming → **Fix agent implementation**

### **Phase 3: WebSocket Message Transmission Verification**

**Objective**: Confirm that streaming messages are being sent via WebSocket.

**Debug Actions**:

1. **Add WebSocket Send Logging**
   ```python
   # In chat_service.py -> _send_websocket_message()
   logger.info(f"📡 [DEBUG] Sending WebSocket message type: {message.get('type')}")
   if message.get('type') == 'message_stream':
       logger.info(f"📡 [DEBUG] Stream phase: start={message.get('stream_start')}, chunk={message.get('stream_chunk')}, end={message.get('stream_end')}")
       if message.get('chunk'):
           logger.info(f"📡 [DEBUG] Chunk content: '{message.get('chunk', '')[:30]}...'")
   ```

2. **Add WebSocket Connection Verification**
   ```python
   # Before sending each streaming message
   active_connections = len([ws_id for ws_id, sess_id in self.chat_sessions.items() if sess_id == session_id])
   logger.info(f"📡 [DEBUG] Active WebSocket connections for session {session_id}: {active_connections}")
   ```

**Expected Results**:
- ✅ Multiple `message_stream` sends: WebSocket sending correctly → **Proceed to Phase 4**
- ❌ No `message_stream` sends: WebSocket issue → **Fix WebSocket layer**

### **Phase 4: Message Routing Debug**

**Objective**: Verify that custom agent messages are routed to the streaming method.

**Debug Actions**:

1. **Add Message Processing Entry Logging**
   ```python
   # In chat_service.py -> process_message()
   logger.info(f"🚦 [DEBUG] Processing message with metadata: {user_message.metadata}")
   
   if user_message.metadata and user_message.metadata.get('agentType'):
       agent_type = user_message.metadata.get('agentType')
       logger.info(f"🚦 [DEBUG] CUSTOM AGENT DETECTED: {agent_type}")
       logger.info(f"🚦 [DEBUG] Calling _process_with_custom_agent({agent_type})")
   else:
       logger.info(f"🚦 [DEBUG] NO CUSTOM AGENT - using default processing")
   ```

2. **Add Routing Decision Logging**
   ```python
   # Before the routing logic
   logger.info(f"🚦 [DEBUG] Routing decision tree:")
   logger.info(f"🚦 [DEBUG] - Has metadata: {bool(user_message.metadata)}")
   logger.info(f"🚦 [DEBUG] - Has agentType: {user_message.metadata.get('agentType') if user_message.metadata else None}")
   logger.info(f"🚦 [DEBUG] - Available custom agents: {get_available_custom_agents()}")
   ```

**Expected Results**:
- ✅ Custom agent detected and routed: Routing working → **Issue is in Phases 1-3**
- ❌ Not detecting custom agent: Routing issue → **Fix message metadata or routing logic**

### **Phase 5: Frontend Message Sending Verification**

**Objective**: Confirm that frontend is sending correct metadata for custom agents.

**Debug Actions**:

1. **Enhanced Frontend Logging** (Already implemented)
   ```typescript
   // Verify this logging exists in chatBackendClient.tsx
   console.log('🎯🎯🎯 HANDLE SEND MESSAGE CALLED 🎯🎯🎯', {messageContent, selectedAgent});
   console.log('🤖 Agent Type Check:', {selectedAgent, customAgents, isCustomAgent, willUseCustomAPI, willUseRegularAPI});
   ```

2. **Add Message Structure Logging**
   ```typescript
   // Before sending WebSocket message
   console.log('📤 [DEBUG] Sending WebSocket message structure:', JSON.stringify(messageToSend, null, 2));
   ```

**Expected Results**:
- ✅ Correct metadata sent: Frontend working → **Issue is backend-side**
- ❌ Missing metadata: Frontend issue → **Fix message construction**

## Debug Execution Order

### **Immediate Priority Debug (Run First)**

1. **Phase 4**: Message routing verification
2. **Phase 1**: Backend streaming activation
3. **Phase 2**: Custom agent output verification

### **Secondary Debug (If First 3 Pass)**

4. **Phase 3**: WebSocket transmission
5. **Phase 5**: Frontend verification

## Known Working Reference

**Main Branch Pattern** (from experience_distillation_stream.md):
```python
# This exact pattern works in main branch
async for message in agent.execute(task, context):
    if message.message_type == "text":
        if is_first_chunk:
            await self._send_streaming_start(...)
            is_first_chunk = False
        await self._send_streaming_chunk(...)
        full_content += message.content
await self._send_streaming_end(...)
```

## Quick Diagnostic Commands

**Backend Log Monitoring**:
```bash
# Monitor backend logs in real-time
tail -f /home/penthoy/icotes/backend/backend.log | grep -E "(DEBUG|process_with_custom_agent|streaming)"
```

**Custom Agent Test**:
```bash
# Test custom agent directly
cd /home/penthoy/icotes/backend
uv run python -c "
from icpy.agent.custom_agent import call_custom_agent_stream
import asyncio

async def test():
    async for chunk in call_custom_agent_stream('OpenAIDemoAgent', 'test', []):
        print(f'Chunk: {chunk}')

asyncio.run(test())
"
```

**WebSocket Message Inspection**:
```javascript
// In browser console
// Monitor all WebSocket messages
const originalOnMessage = WebSocket.prototype.onmessage;
WebSocket.prototype.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'message_stream') {
        console.log('🟢 STREAMING MESSAGE:', data);
    } else if (data.type === 'message') {
        console.log('🔴 COMPLETE MESSAGE:', data);
    }
    return originalOnMessage.call(this, event);
};
```

## Success Criteria

**✅ Streaming Working When**:
- Frontend logs show `type: 'message_stream'` messages
- Backend logs show streaming start/chunk/end sequence
- Custom agent yields multiple small chunks
- WebSocket sends three-phase protocol messages
- Real-time character-by-character appearance in UI

**🎯 Expected Fix Location**:
Based on evidence, the most likely issue is in **message routing** or **streaming method activation**. The implementation is correct, but something prevents the streaming path from executing.

---

*This debug plan provides systematic verification of each layer in the streaming pipeline. Execute phases in order until the break point is identified.*
