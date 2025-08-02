# WebSocket Architecture Plan

## Current State Analysis

### Existing Endpoints
1. `/ws` - Centralized service (File operations, Explorer, code execution, general messaging)
2. `/ws/terminal/{id}` - Direct terminal connection
3. `/ws/chat` - Direct chat/AI agent connection (**NOT a duplicate**)

### Issues Identified
1. **Inconsistent Connection Management** - Terminal waits for centralized service ✅ FIXED
2. **Service Overlap Confusion** - Need to clarify which service handles what
3. **Multiple Connections Per Client** - Resource overhead (acceptable for now)
4. **Complex Error Handling** - Different failure modes per connection

## Service Responsibilities Clarified

After analysis, the endpoints are **NOT duplicates** but serve different purposes:

### `/ws` (Centralized Service)
- **File operations** (read, write, list directories)
- **Code execution** (Python, JavaScript)
- **JSON-RPC protocol** support
- **Explorer functionality** (file browsing)
- **System notifications**
- **Generic pub/sub messaging**

### `/ws/chat` (Dedicated Chat Service)  
- **AI agent conversations**
- **Real-time chat streaming**
- **Chat history management**
- **Agent configuration**
- **Custom agent interactions**

### `/ws/terminal/{id}` (Dedicated Terminal Service)
- **Direct PTY communication**
- **Binary terminal data**
- **Low-latency I/O**
- **Terminal resizing**
- **Shell command execution**

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

#### Phase 1: Update Documentation ✅ COMPLETED  
1. ~~Remove `/ws/chat` endpoint (use `/ws` instead)~~ **NOT NEEDED - Services are distinct**
2. ~~Consolidate chat functionality in centralized service~~ **NOT NEEDED - Chat has dedicated service**
3. Document service responsibilities clearly ✅ DONE

#### Phase 2: Improve Connection Independence ✅ COMPLETED
1. Make terminal connection truly independent ✅ DONE
2. Remove terminal dependency on centralized service status ✅ DONE  
3. Add separate connection status tracking per service ✅ IMPLEMENTED

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

### Step 2: ~~Consolidate Chat Services~~ **NOT NEEDED**
- [x] **Analysis Complete** - `/ws/chat` serves distinct purpose from `/ws`
- [x] **Services Clarified** - Chat service handles AI agents, centralized service handles files/code
- [x] **No Consolidation Required** - Each service optimized for its use case

### Step 3: ~~Fix Terminal Independence~~ ✅ **COMPLETED**
- [x] Remove terminal dependency on centralized service  
- [x] Add separate terminal connection status tracking
- [x] Implement robust terminal reconnection

### Step 4: Implement Architecture Improvements 🚀 **RECOMMENDED**
- [ ] **Unified Connection Manager** - Centralize connection logic across all services
- [ ] **Standardized Error Handling** - Consistent error types and recovery strategies  
- [ ] **Performance Optimizations** - Message batching, connection pooling
- [ ] **Health Monitoring** - Real-time connection diagnostics
- [ ] **Developer Experience** - Debug dashboard, better logging

*See [websocket_implementation_improvements.md](./websocket_implementation_improvements.md) for detailed implementation plan*

## Success Metrics
1. **Latency** - Terminal response time < 10ms
2. **Reliability** - 99.9% connection uptime per service
3. **Resource Usage** - Reduce total connections by 30%
4. **Error Recovery** - Independent service recovery
5. **Developer Experience** - Clear connection status per service

## Conclusion ✅ **ANALYSIS COMPLETE**

**The current architecture is well-designed and NOT problematic:**

1. **`/ws/chat` is NOT a duplicate** - It's a specialized service for AI agent interactions
2. **Each service serves distinct purposes** - Files/code vs Chat vs Terminal
3. **Performance trade-offs are appropriate** - Direct connections for high-performance services
4. **The terminal connection issue was implementation, not architecture** ✅ FIXED

**Current Status: Architecture is sound, terminal connection fixed, no major changes needed.**
