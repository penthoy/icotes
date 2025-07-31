# WebSocket Architecture Plan

## Current State Analysis

### Existing Endpoints
1. `/ws` - Centralized service (Chat, Explorer, general messaging)
2. `/ws/terminal/{id}` - Direct terminal connection
3. `/ws/chat` - Direct chat connection (duplicate?)

### Issues Identified
1. **Inconsistent Connection Management** - Terminal waits for centralized service
2. **Duplicate Chat Endpoints** - Both `/ws` and `/ws/chat` handle chat
3. **Resource Overhead** - Multiple connections per client
4. **Complex Error Handling** - Different failure modes per connection

## Recommended Hybrid Architecture

### Service Classification

#### High-Performance Direct Connections
**Use dedicated endpoints for performance-critical services:**

- **`/ws/terminal/{id}`** - Keep direct for low-latency I/O
  - Binary data support
  - Direct PTY communication
  - Independent from other services
  
- **`/ws/file-stream/{operation_id}`** - For large file operations
  - File uploads/downloads
  - Binary file content
  - Progress streaming

#### Unified Message-Based Connection
**Use centralized endpoint for request/response patterns:**

- **`/ws`** - Enhanced centralized service
  - Chat/AI messages
  - File CRUD operations
  - Directory listing
  - System notifications
  - Service status updates

### Implementation Strategy

#### Phase 1: Clean Up Duplicates
1. Remove `/ws/chat` endpoint (use `/ws` instead)
2. Consolidate chat functionality in centralized service
3. Update frontend to use unified chat connection

#### Phase 2: Improve Connection Independence
1. Make terminal connection truly independent
2. Remove terminal dependency on centralized service status
3. Add separate connection status tracking per service

#### Phase 3: Enhanced Message Routing
1. Implement proper message typing in centralized service
2. Add connection pooling and load balancing
3. Implement message prioritization

## Frontend Connection Strategy

### Connection Manager Pattern
```typescript
class ConnectionManager {
  private mainConnection: WebSocket;      // /ws - chat, files, notifications
  private terminalConnections: Map<string, WebSocket>; // /ws/terminal/{id}
  private fileStreamConnections: Map<string, WebSocket>; // /ws/file-stream/{id}
  
  // Independent connection status per service
  getConnectionStatus(service: 'main' | 'terminal' | 'file-stream'): ConnectionStatus;
  
  // Service-specific connection methods
  connectTerminal(terminalId: string): Promise<WebSocket>;
  connectFileStream(operationId: string): Promise<WebSocket>;
  connectMain(): Promise<WebSocket>;
}
```

### Benefits of Hybrid Approach
1. **Performance** - Direct connections for high-throughput services
2. **Consistency** - Unified connection for standard operations  
3. **Independence** - Services can fail independently
4. **Scalability** - Can optimize each connection type separately
5. **Backward Compatibility** - Existing terminal code works unchanged

## Migration Plan

### Step 1: Audit Current Usage
- [ ] Map all WebSocket endpoints and their usage
- [ ] Identify duplicate functionality
- [ ] Document current connection dependencies

### Step 2: Consolidate Chat Services
- [ ] Remove `/ws/chat` endpoint
- [ ] Update chat UI to use `/ws` endpoint
- [ ] Test chat functionality through centralized service

### Step 3: Fix Terminal Independence
- [ ] Remove terminal dependency on centralized service
- [ ] Add separate terminal connection status tracking
- [ ] Implement robust terminal reconnection

### Step 4: Optimize Message Routing
- [ ] Implement typed message routing in `/ws`
- [ ] Add connection pooling for performance
- [ ] Implement message queuing and replay

## Success Metrics
1. **Latency** - Terminal response time < 10ms
2. **Reliability** - 99.9% connection uptime per service
3. **Resource Usage** - Reduce total connections by 30%
4. **Error Recovery** - Independent service recovery
5. **Developer Experience** - Clear connection status per service

## Conclusion
The hybrid approach balances performance, maintainability, and user experience by using the right connection type for each service's requirements.
