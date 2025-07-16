# Backend Rewrite Plan - Modular Service Architecture (ICPI)

## Overview
This document outlines the step-by-step plan for rewriting the backend with a modular, event-driven architecture that serves as a single source of truth for the frontend. The new system will provide a unified API layer accessible via WebSocket, HTTP, and CLI interfaces, enabling real-time collaboration between frontend components and external tools.

## Design Principles
1. **Single Source of Truth**: Backend maintains the authoritative state
2. **Event-Driven Architecture**: Services communicate via message broker
3. **Unified API Layer**: Single protocol for WebSocket, HTTP, and CLI access
4. **Modular Services**: Independent, replaceable service components
5. **Real-time Synchronization**: Immediate state updates across all clients
6. **Extensible Design**: Easy addition of new services and features

## Current Backend Analysis

### Existing Structure
- **FastAPI Application**: Single monolithic server in `backend/main.py`
- **Terminal Management**: PTY-based terminal sessions in `backend/terminal.py`
- **Clipboard System**: Server-side clipboard with system integration
- **Code Execution**: Python code execution with output capture
- **WebSocket Support**: Basic WebSocket endpoints for terminal and general communication

### Current Limitations
- Monolithic structure with tight coupling
- No unified communication protocol
- Limited service separation
- No event-driven architecture
- No CLI interface
- No real-time state synchronization
- Difficult to extend with new features

## Implementation Steps

### Phase 1: Message Broker Foundation
**Goal**: Create the central nervous system for all backend communication

#### Step 1.1: Message Broker Implementation
- Create `backend/core/message_broker.py`
- Implement in-memory event bus using `asyncio.Queue`
- Support event subscription and publishing
- Add message routing and filtering
- Include message persistence for recovery
- **Integration Test**: `tests/backend/test_message_broker.py`

#### Step 1.2: JSON-RPC Protocol Definition
- Create `backend/core/protocol.py`
- Define standardized message format for all communication
- Support request/response and notification patterns
- Include error handling and validation
- Add message serialization/deserialization
- **Integration Test**: `tests/backend/test_protocol.py`

#### Step 1.3: Connection Manager
- Create `backend/core/connection_manager.py`
- Manage WebSocket, HTTP, and CLI connections
- Handle client authentication and session management
- Support connection pooling and cleanup
- Add connection health monitoring
- **Integration Test**: `tests/backend/test_connection_manager.py`

### Phase 2: Core Services Foundation
**Goal**: Create the essential services that form the backbone of the system

#### Step 2.1: Workspace Service
- Create `backend/services/workspace_service.py`
- Maintain application state (open files, active panels, etc.)
- Handle workspace initialization and persistence
- Manage user preferences and settings
- Support workspace switching and management
- **Integration Test**: `tests/backend/test_workspace_service.py`

#### Step 2.2: File System Service
- Create `backend/services/filesystem_service.py`
- Handle all file operations (read, write, delete, list)
- Implement file watching for external changes
- Support file search and indexing
- Add file type detection and handling
- **Integration Test**: `tests/backend/test_filesystem_service.py`

#### Step 2.3: Terminal Service Refactor
- Refactor `backend/terminal.py` into `backend/services/terminal_service.py`
- Integrate with message broker architecture
- Support multiple terminal instances
- Add terminal session management
- Include terminal configuration and customization
- **Integration Test**: `tests/backend/test_terminal_service.py`

### Phase 3: Unified API Gateway
**Goal**: Create a single entry point that handles all communication protocols

#### Step 3.1: API Gateway Implementation
- Create `backend/gateway/api_gateway.py`
- Handle WebSocket connections at `/ws`
- Support HTTP REST endpoints at `/api/*`
- Add CLI interface via command-line arguments
- Implement protocol translation and routing
- **Integration Test**: `tests/backend/test_api_gateway.py`

#### Step 3.2: CLI Interface
- Create `backend/cli/icotes_cli.py`
- Support `icotes file.py` command to open files
- Add `icotes --terminal` for terminal access
- Include `icotes --api` for direct API calls
- Support AI tool integration via CLI
- **Integration Test**: `tests/backend/test_cli_interface.py`

#### Step 3.3: HTTP REST API
- Create `backend/api/rest_endpoints.py`
- Implement file operations endpoints
- Add terminal management endpoints
- Include workspace management endpoints
- Support clipboard operations
- **Integration Test**: `tests/backend/test_rest_api.py`

### Phase 4: Real-time State Synchronization
**Goal**: Enable real-time updates across all connected clients

#### Step 4.1: State Synchronization Service
- Create `backend/services/state_sync_service.py`
- Maintain client state mapping
- Handle state diffing and updates
- Support partial state updates
- Add conflict resolution
- **Integration Test**: `tests/backend/test_state_sync_service.py`

#### Step 4.2: Event Broadcasting System
- Create `backend/core/event_broadcaster.py`
- Broadcast events to all connected clients
- Support targeted event delivery
- Add event filtering and routing
- Include event history and replay
- **Integration Test**: `tests/backend/test_event_broadcaster.py`

#### Step 4.3: Client State Management
- Create `backend/core/client_state_manager.py`
- Track client connections and state
- Handle client disconnection and reconnection
- Support state recovery for reconnected clients
- Add client activity monitoring
- **Integration Test**: `tests/backend/test_client_state_manager.py`

### Phase 5: Advanced Services
**Goal**: Add specialized services for enhanced functionality

#### Step 5.1: Code Execution Service
- Create `backend/services/code_execution_service.py`
- Support multiple programming languages
- Add sandboxed execution environments
- Include execution result caching
- Support interactive code execution
- **Integration Test**: `tests/backend/test_code_execution_service.py`

#### Step 5.2: Clipboard Service Enhancement
- Refactor clipboard functionality into `backend/services/clipboard_service.py`
- Support multiple clipboard types (text, files, images)
- Add clipboard history and management
- Include cross-platform clipboard integration
- Support clipboard sharing between clients
- **Integration Test**: `tests/backend/test_clipboard_service.py`

#### Step 5.3: AI Integration Service
- Create `backend/services/ai_integration_service.py`
- Support AI tool communication
- Add file editing via AI commands
- Include AI context management
- Support AI-assisted code generation
- **Integration Test**: `tests/backend/test_ai_integration_service.py`

### Phase 6: Service Discovery and Registry
**Goal**: Create a system for dynamic service management

#### Step 6.1: Service Registry
- Create `backend/core/service_registry.py`
- Register and discover available services
- Support service health monitoring
- Add service dependency management
- Include service configuration management
- **Integration Test**: `tests/backend/test_service_registry.py`

#### Step 6.2: Service Lifecycle Management
- Create `backend/core/service_lifecycle.py`
- Handle service startup and shutdown
- Support service restart and recovery
- Add service dependency resolution
- Include service health checks
- **Integration Test**: `tests/backend/test_service_lifecycle.py`

#### Step 6.3: Plugin System
- Create `backend/core/plugin_system.py`
- Support dynamic service loading
- Add plugin configuration management
- Include plugin dependency handling
- Support plugin hot-reloading
- **Integration Test**: `tests/backend/test_plugin_system.py`

### Phase 7: Performance and Monitoring
**Goal**: Add performance optimization and monitoring capabilities

#### Step 7.1: Performance Monitoring
- Create `backend/monitoring/performance_monitor.py`
- Track service performance metrics
- Add request/response timing
- Include resource usage monitoring
- Support performance alerts
- **Integration Test**: `tests/backend/test_performance_monitor.py`

#### Step 7.2: Caching System
- Create `backend/core/cache_manager.py`
- Implement multi-level caching
- Support cache invalidation
- Add cache statistics and monitoring
- Include distributed caching support
- **Integration Test**: `tests/backend/test_cache_manager.py`

#### Step 7.3: Load Balancing
- Create `backend/core/load_balancer.py`
- Distribute load across multiple instances
- Support service scaling
- Add health-based routing
- Include load monitoring
- **Integration Test**: `tests/backend/test_load_balancer.py`

### Phase 8: Security and Authentication
**Goal**: Implement comprehensive security measures

#### Step 8.1: Authentication Service
- Create `backend/services/auth_service.py`
- Support multiple authentication methods
- Add session management
- Include permission-based access control
- Support API key management
- **Integration Test**: `tests/backend/test_auth_service.py`

#### Step 8.2: Security Middleware
- Create `backend/middleware/security.py`
- Implement request validation
- Add rate limiting
- Include input sanitization
- Support CORS and security headers
- **Integration Test**: `tests/backend/test_security_middleware.py`

#### Step 8.3: Audit Logging
- Create `backend/services/audit_service.py`
- Log all system activities
- Add audit trail management
- Include compliance reporting
- Support log analysis
- **Integration Test**: `tests/backend/test_audit_service.py`

## File Structure
```
backend/
├── core/
│   ├── __init__.py
│   ├── message_broker.py
│   ├── protocol.py
│   ├── connection_manager.py
│   ├── service_registry.py
│   ├── service_lifecycle.py
│   ├── plugin_system.py
│   ├── cache_manager.py
│   ├── load_balancer.py
│   ├── event_broadcaster.py
│   └── client_state_manager.py
├── services/
│   ├── __init__.py
│   ├── workspace_service.py
│   ├── filesystem_service.py
│   ├── terminal_service.py
│   ├── code_execution_service.py
│   ├── clipboard_service.py
│   ├── ai_integration_service.py
│   ├── state_sync_service.py
│   ├── auth_service.py
│   └── audit_service.py
├── gateway/
│   ├── __init__.py
│   ├── api_gateway.py
│   └── websocket_handler.py
├── api/
│   ├── __init__.py
│   ├── rest_endpoints.py
│   └── websocket_endpoints.py
├── cli/
│   ├── __init__.py
│   ├── icotes_cli.py
│   └── commands.py
├── middleware/
│   ├── __init__.py
│   ├── security.py
│   └── logging.py
├── monitoring/
│   ├── __init__.py
│   ├── performance_monitor.py
│   └── health_checker.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── environment.py
├── utils/
│   ├── __init__.py
│   ├── file_utils.py
│   ├── terminal_utils.py
│   └── validation.py
├── main.py
├── requirements.txt
└── README.md
```

## Integration Tests Structure
```
tests/
├── backend/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_message_broker.py
│   ├── test_protocol.py
│   ├── test_connection_manager.py
│   ├── test_workspace_service.py
│   ├── test_filesystem_service.py
│   ├── test_terminal_service.py
│   ├── test_api_gateway.py
│   ├── test_cli_interface.py
│   ├── test_rest_api.py
│   ├── test_state_sync_service.py
│   ├── test_event_broadcaster.py
│   ├── test_client_state_manager.py
│   ├── test_code_execution_service.py
│   ├── test_clipboard_service.py
│   ├── test_ai_integration_service.py
│   ├── test_service_registry.py
│   ├── test_service_lifecycle.py
│   ├── test_plugin_system.py
│   ├── test_performance_monitor.py
│   ├── test_cache_manager.py
│   ├── test_load_balancer.py
│   ├── test_auth_service.py
│   ├── test_security_middleware.py
│   └── test_audit_service.py
└── integration/
    ├── __init__.py
    ├── test_full_workflow.py
    ├── test_multi_client_sync.py
    ├── test_cli_integration.py
    └── test_ai_tool_integration.py
```

## Migration Strategy
1. **Phase 1-2**: Build foundation without touching existing functionality
2. **Phase 3**: Create new API gateway alongside existing endpoints
3. **Phase 4**: Implement real-time synchronization
4. **Phase 5**: Add advanced services and features
5. **Phase 6**: Implement service discovery and plugin system
6. **Phase 7**: Add performance optimization and monitoring
7. **Phase 8**: Implement security and authentication
8. **Phase 9**: Gradual migration from old to new system
9. **Phase 10**: Complete migration and cleanup

## Testing Strategy
- **Unit Tests**: Test individual service components
- **Integration Tests**: Test service interactions and workflows
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test system performance under load
- **Security Tests**: Test authentication and authorization
- **Load Tests**: Test system behavior under high load

## Rollback Plan
- Keep existing backend intact during development
- Implement feature flags for new functionality
- Maintain backward compatibility during transition
- Document migration path and rollback procedures
- Create automated rollback scripts

## Timeline Estimate
- Phase 1: 3-4 days (Message broker foundation)
- Phase 2: 4-5 days (Core services)
- Phase 3: 3-4 days (API gateway and CLI)
- Phase 4: 3-4 days (Real-time synchronization)
- Phase 5: 4-5 days (Advanced services)
- Phase 6: 2-3 days (Service discovery)
- Phase 7: 3-4 days (Performance and monitoring)
- Phase 8: 3-4 days (Security and authentication)
- Testing and refinement: 4-5 days
- Migration and cleanup: 3-4 days

**Total estimated time**: 32-42 days

## Success Criteria
- [ ] Single WebSocket connection handles all communication
- [ ] CLI interface supports `icotes file.py` command
- [ ] AI tools can interact with backend via unified API
- [ ] Real-time file browser updates when files are created/modified
- [ ] Multiple clients can collaborate on same workspace
- [ ] Services are modular and independently replaceable
- [ ] Performance remains optimal under load
- [ ] Security measures are comprehensive
- [ ] Existing functionality is preserved
- [ ] Migration path is smooth and non-disruptive
- [ ] All integration tests pass
- [ ] Documentation is complete and up-to-date

## Key Features for User Requirements

### Unified API Layer
- **CLI Interface**: `icotes file.py` opens file in editor
- **AI Tool Integration**: AI can make real-time edits via API
- **Real-time Updates**: File browser updates immediately when files change
- **Multi-protocol Support**: WebSocket, HTTP, and CLI all use same protocol

### Extensibility for Future Features
- **Notepad Support**: Rich text editor panel (future)
- **Jupyter-like Features**: Interactive notebook functionality (future)
- **Plugin System**: Easy addition of new services and features
- **Service Architecture**: Modular design for easy extension

### Performance and Reliability
- **Event-driven Architecture**: Efficient communication between services
- **Caching System**: Optimized performance for file operations
- **Load Balancing**: Support for multiple backend instances
- **Health Monitoring**: Comprehensive system monitoring

---

*This plan provides a comprehensive roadmap for creating a modern, modular backend architecture that meets all current requirements while providing a solid foundation for future enhancements.* 