# SSH Hop Connection Persistence Issue in Docker

## Issue Description
The SSH Hop panel in Docker containers was not persisting connection state properly. After connecting to a remote host, the connection status would not persist, and the Hop button would disappear when switching back to local context. This required repeated reconnections.

## Root Cause Analysis

### 1. WebSocket Auto-Subscription Gap
The WebSocket backend only auto-subscribed connections to `fs.*` (filesystem events) by default, but NOT to `hop.*` (SSH hop events). This meant:

- When a WebSocket connection was established (or re-established after a disconnect), clients were automatically subscribed to filesystem events
- However, hop events required explicit subscription from the frontend
- If the explicit subscription request failed or timed out (more common in Docker due to networking), the UI would never receive hop status updates

### 2. Event-Driven UI Updates
The `ICUIHop` component relies entirely on WebSocket events to update its state:

- `hop_status` events: Update the current session status (local vs remote)
- `hop_event` events: Handle credential changes and session list updates
- Without these events, the UI doesn't know about connection state changes

### 3. Docker Networking Challenges
Docker containers experience more frequent WebSocket reconnections due to:

- Container restarts
- Network bridge reconfigurations
- Resource constraints leading to temporary disconnects

Each reconnection required re-subscription to `hop.*`, and failures in this process would leave the UI in an inconsistent state.

## Solution

### Backend Fix: Add `hop.*` to Default Subscriptions
**File**: `backend/icpy/api/websocket_api.py`

Added `hop.*` to the default auto-subscriptions:

```python
# Apply safe default subscriptions so clients receive critical events even
# if they miss initial subscribe timing on first load/reconnect.
# Keep this conservative: filesystem events are needed by Explorer UI.
# hop.* is needed for SSH Hop panel to maintain connection state across reconnects.
default_topics = {"fs.*", "hop.*"}
connection.subscriptions.update(default_topics)
```

**Benefits**:
- Ensures hop events are always delivered, even if explicit subscription fails
- Critical for Docker environments where reconnections are more frequent
- Minimal overhead since hop events are only published when SSH operations occur

### Frontend Fix: Add Reconnection Resilience
**File**: `src/icui/components/panels/ICUIHop.tsx`

Enhanced the subscription logic with:

1. **Retry mechanism**: Attempts subscription up to 3 times with exponential backoff
2. **Connection status monitoring**: Listens for `connection_status_changed` events
3. **Auto-resubscribe on reconnect**: When connection is restored, automatically resubscribes and reloads state

```typescript
// Subscribe with retry logic
const subscribeWithRetry = async (retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      await (backendService as any).notify?.('subscribe', { topics: ['hop.*'] });
      logHop('Successfully subscribed to hop.* events', { attempt: i + 1 });
      break;
    } catch (e) {
      if (i === retries - 1) {
        console.warn('[HopUI] Failed to subscribe to hop.* after retries:', e);
      } else {
        await new Promise(resolve => setTimeout(resolve, 500 * (i + 1)));
      }
    }
  }
};

// Handle connection status changes
const onConnectionStatusChanged = (status: any) => {
  if (status.status === 'connected') {
    subscribeWithRetry();
    load();
  }
};
```

**Benefits**:
- Gracefully handles subscription failures with retries
- Automatically recovers from WebSocket disconnections
- Improves user experience in unstable network conditions

## Testing

### Verify the Fix

1. **Start Docker container**:
   ```bash
   docker-compose up
   ```

2. **Connect to a remote host** via SSH Hop panel
3. **Switch back to local** context using "Hop to local" button
4. **Verify**:
   - Connection persists in the sessions list
   - Hop button remains visible for the connected remote host
   - No need to reconnect

### Test Reconnection Resilience

1. **Connect to remote host**
2. **Restart Docker container**:
   ```bash
   docker-compose restart icotes-app
   ```
3. **Verify**:
   - After container restart, reload the page
   - SSH session should be restored
   - Connection state should be visible in the UI

## Impact

- **Improves Docker deployment stability**: SSH Hop feature now works reliably in containerized environments
- **Better UX**: No need for repeated reconnections when switching contexts
- **Minimal overhead**: Only adds one additional topic to default subscriptions
- **Backward compatible**: Local installations continue to work as before

## Related Files

- `backend/icpy/api/websocket_api.py` - WebSocket auto-subscription logic
- `src/icui/components/panels/ICUIHop.tsx` - Hop UI component
- `backend/tests/icpy/test_websocket_api.py` - Updated test expectations
