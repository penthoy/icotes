# ICPI Backend Implementation Plan - Modular Event-Driven Architecture

## Overview
This document outlines the comprehensive plan for rewriting the icotes backend into a modular, event-driven architecture that serves as a single source of truth for the frontend. The new system will provide a unified API layer accessible via WebSocket, HTTP, and CLI interfaces, enabling real-time collaboration between frontend components and external tools including AI agents.

## Mission Statement
Create a backend that acts as a **single source of truth** for the frontend, is highly performant, modular, and built for extensibility. The architecture will support real-time updates across all connected clients and provide seamless integration for AI tools and command-line interfaces through the `icpy` command.

## Core Design Principles

1. **Single Source of Truth**: Backend maintains the authoritative state for all workspace elements
2. **Event-Driven Architecture**: Services communicate asynchronously via a central message broker
3. **Unified API Layer**: Single protocol for WebSocket, HTTP, and CLI access enabling commands like `icotes file.py`
4. **Modular Services**: Independent, swappable service components with clear boundaries
5. **Real-time Synchronization**: Immediate state updates across all clients and tools
6. **Extensible Design**: Easy addition of new services (future rich text editor, AI agents) without rewrites
7. **Test-Driven Development**: Comprehensive integration tests for each phase

## Current Backend Analysis

### Existing Structure
- **FastAPI Application**: Monolithic server in `backend/icpy/main.py` (788 lines)
- **Terminal Management**: PTY-based terminal sessions in `backend/icpy/terminal.py` (305 lines)
- **Clipboard System**: Server-side clipboard with system integration
- **Code Execution**: Python code execution with output capture
- **WebSocket Support**: Basic WebSocket endpoints for terminal and general communication

### Current Limitations
- Monolithic structure with tight coupling between components
- No unified communication protocol for different client types
- Limited service separation - all functionality in main.py
- No event-driven architecture for real-time updates
- No CLI interface for external tool integration
- No real-time state synchronization across clients
- Difficult to extend with new features (rich text editor, AI agents)

## Implementation Phases

### Phase 1: Core Infrastructure Foundation
**Goal**: Establish the fundamental messaging and communication infrastructure

#### Step 1.1: Message Broker Implementation
- Create `backend/icpy/core/message_broker.py`
- Implement in-memory event bus using `asyncio.Queue` and `asyncio.Event`
- Support topic-based subscription system with wildcard patterns
- Add message validation, routing, and filtering capabilities
- Include message persistence and replay for client recovery
- Support both request/response and notification patterns
- Consider RxJS-inspired reactive programming patterns for event handling
- **Integration Test**: `tests/backend/icpy/test_message_broker.py`
  - Basic pub/sub functionality
  - Message routing and filtering
  - Error conditions and recovery
  - Performance under load
  - Reactive programming patterns

#### Step 1.2: JSON-RPC Protocol Definition
- Create `backend/icpy/core/protocol.py`
- Define standardized message format for all communication (WebSocket, HTTP, CLI)
- Support JSON-RPC 2.0 specification with extensions
- Include error handling, validation, and message serialization
- Add protocol versioning for future compatibility
- **Integration Test**: `tests/backend/icpy/test_protocol.py`
  - Message validation and serialization
  - Error handling and edge cases
  - Protocol versioning

#### Step 1.3: Connection Manager and API Gateway ✅ COMPLETED
- Create `backend/icpy/core/connection_manager.py`
- Manage WebSocket, HTTP, and CLI connections with session tracking
- Handle client authentication and authorization
- Support connection pooling, health monitoring, and cleanup
- Create `backend/icpy/gateway/api_gateway.py` as single entry point
- **Integration Test**: `tests/backend/icpy/test_connection_manager.py`
  - Connection lifecycle management
  - Authentication flows
  - Health monitoring and cleanup
- **Status**: ✅ Complete - 53 integration tests covering connection management and API gateway

### Phase 2: Core Services Foundation
**Goal**: Refactor existing functionality into modular services

#### Step 2.1: Workspace Service ✅ COMPLETED
- Create `backend/icpy/services/workspace_service.py`
- Maintain application state (open files, active terminals, panels, etc.)
- Handle workspace initialization, persistence, and switching
- Manage user preferences and workspace configuration
- Publish `workspace.state_changed` events for real-time updates
- **Integration Test**: `tests/backend/icpy/test_workspace_service.py`
  - State management and persistence
  - Event publishing on state changes
  - Multi-client synchronization
- **Status**: ✅ Complete - 19 integration tests covering workspace management, file operations, panels, terminals, layouts, preferences, persistence, events, and concurrent operations

#### Step 2.2: File System Service
✅ **COMPLETED**
- Created `backend/icpy/services/filesystem_service.py`
- Implemented comprehensive file CRUD operations with async support
- Added file type classification and metadata extraction
- Implemented file watching with `watchdog` for real-time change detection
- Added file search and indexing capabilities for fast file discovery
- Implemented file permissions and access control
- Added event-driven architecture with message broker integration
- Included content caching for performance optimization
- **Integration Test**: `tests/backend/icpy/test_filesystem_service.py` - ✅ ALL 26 TESTS PASSING
  - CRUD operations and error handling
  - File watching and change detection
  - File search and indexing
  - Real-time event publishing

#### Step 2.3: Terminal Service Refactor
✅ **COMPLETED**
- Refactored `backend/icpy/terminal.py` into `backend/icpy/services/terminal_service.py`
- Integrated with message broker architecture for event-driven communication
- Added support for multiple terminal instances with independent sessions
- Implemented terminal session management and configuration
- Maintained existing PTY functionality while adding event-driven communication
- Added comprehensive terminal lifecycle management (create, start, stop, destroy)
- Implemented WebSocket connection handling for real-time I/O
- Added terminal resizing, input/output handling, and session statistics
- Included session cleanup and resource management
- Added Google-style docstrings for all methods
- **Integration Test**: `tests/backend/icpy/test_terminal_service.py` - ✅ ALL 33 TESTS PASSING
  - Terminal creation and lifecycle management
  - Input/output handling via events and WebSocket connections
  - Multiple terminal management with independent sessions
  - Session configuration and environment handling
  - Error handling and resource cleanup
  - Message broker integration for event-driven operations

### Phase 3: Unified API Layer
**Goal**: Create single interfaces for all client types

#### Step 3.1: WebSocket API Enhancement ✅ COMPLETE
- ✅ Enhanced existing WebSocket handling in `backend/main.py`
- ✅ Integrated with message broker for real-time communication
- ✅ Support multiple concurrent connections with state synchronization
- ✅ Added connection recovery and message replay capabilities
- ✅ **Integration Test**: `tests/backend/test_websocket_api.py`
  - ✅ Real-time state synchronization
  - ✅ Connection recovery
  - ✅ Multi-client coordination

**Implementation Details**:
- Created `backend/icpy/api/websocket_api.py` with enhanced WebSocket API
- Implemented `WebSocketAPI` class with message broker integration
- Added connection management with state tracking and cleanup
- Supports JSON-RPC protocol over WebSocket
- Provides real-time event broadcasting to subscribed clients
- Includes connection recovery with message replay
- Added comprehensive test suite with 27 passing tests
- Enhanced `backend/main.py` with new WebSocket endpoints
- **Tests**: All 27 tests in `tests/icpy/test_websocket_api.py` pass
- **Files Created**: `backend/icpy/api/websocket_api.py`, `backend/icpy/api/__init__.py`
- **Status**: Complete and tested

#### Step 3.2: HTTP REST API
- Create `backend/icpy/api/rest_api.py`
- Implement RESTful endpoints for all services
- Support file operations, terminal management, and workspace operations
- Add OpenAPI/Swagger documentation
- **Integration Test**: `tests/backend/icpy/test_rest_api.py`
  - CRUD operations via HTTP
  - Error handling and validation
  - API documentation accuracy
- **Status**: Complete and tested

#### Step 3.3: CLI Interface Implementation ✅ COMPLETE
- ✅ Created `backend/icpy/cli/icpy_cli.py` with comprehensive CLI interface
- ✅ Implemented commands like `icpy file.py` to open files in editor
- ✅ Added `icpy --terminal` for terminal access
- ✅ Included `icpy --workspace` for workspace management
- ✅ Enabled AI tools to interact via CLI for real-time editing
- ✅ **Integration Test**: `tests/backend/icpy/test_cli_interface.py`
  - ✅ Test `icpy file.py` opens files
  - ✅ Test `icpy --terminal` starts terminal session
  - ✅ Test `icpy --workspace` manages workspaces
  - ✅ File opening and editor integration
  - ✅ Terminal access and management
  - ✅ AI tool integration scenarios

**Implementation Details**:
- Created `backend/icpy/cli/icpy_cli.py` with full CLI interface
- Implemented `backend/icpy/cli/http_client.py` for HTTP communication
- Added `backend/icpy/cli/command_handlers.py` for command processing
- Created `backend/icpy_cli.py` as executable entry point
- Supports file operations, terminal management, and workspace operations
- Includes interactive mode for continuous CLI operation
- Integrates with icpy backend REST API for all operations
- Provides comprehensive error handling and user feedback
- Added Google-style docstrings for all methods
- Comprehensive test coverage with functionality verification
- **Tests**: All CLI functionality tests pass including help, status, and workspace commands
- **Files Created**: `backend/icpy/cli/` directory with full CLI implementation
- **Status**: Complete - Phase 3.3 of icpy_plan.md implemented and tested

## MILESTONE 1: Frontend Integration Ready
**Completion**: After Phase 3
**Purpose**: The backend now has feature parity with the current implementation and is ready for frontend integration.

### Features Available:
1. **Core Infrastructure**
   - Message broker for event-driven communication
   - JSON-RPC protocol for all client interactions
   - Connection management for WebSocket and HTTP

2. **Core Services**
   - Workspace management (open files, panels, state)
   - File system operations with change notifications
   - Terminal sessions with PTY support

3. **API Layer**
   - WebSocket API for real-time communication
   - REST API for traditional HTTP requests
   - CLI interface for external tools

### Frontend Integration Points:
- Connect to WebSocket endpoint for real-time updates
- Use REST API for file operations and terminal management
- Implement CLI commands for tool integration

### Testing Status:
- All core features have integration tests
- API contracts are stable
- Backward compatibility with existing frontend endpoints

---

### Phase 4: Real-time State Synchronization
**Goal**: Enable seamless real-time updates across all clients

#### Step 4.1: State Synchronization Service
- Create `backend/icpy/services/state_sync_service.py`
- Maintain client state mapping and synchronization
- Handle state diffing and incremental updates
- Support conflict resolution for concurrent edits
- Add client presence awareness (who's viewing what)
- **Integration Test**: `tests/backend/icpy/test_state_sync_service.py`
  - Multi-client state synchronization
  - Conflict resolution
  - Presence awareness

#### Step 4.2: Event Broadcasting System
- Create `backend/icpy/core/event_broadcaster.py`
- Broadcast events to all connected clients (WebSocket, HTTP long-polling)
- Support targeted event delivery based on client interests
- Add event filtering and routing based on permissions
- Include event history and replay for disconnected clients
- **Integration Test**: `tests/backend/icpy/test_event_broadcaster.py`
  - Event broadcasting to multiple clients
  - Targeted delivery and filtering
  - Event history and replay

### Phase 5: Enhanced Services
**Goal**: Add advanced functionality and prepare for future features

#### Step 5.1: Code Execution Service
- Refactor existing code execution from `backend/main.py`
- Create `backend/icpy/services/code_execution_service.py`
- Support multiple programming languages and sandboxed execution
- Add execution result caching and history
- Support interactive code execution with real-time output
- **Integration Test**: `tests/backend/icpy/test_code_execution_service.py`
  - Multi-language execution
  - Sandboxed execution safety
  - Real-time output streaming

#### Step 5.2: Enhanced Clipboard Service
- Refactor existing clipboard functionality from `backend/main.py`
- Create `backend/icpy/services/clipboard_service.py`
- Maintain existing system clipboard integration
- Add clipboard history and cross-client synchronization
- Support rich content types (future: images, formatted text)
- **Integration Test**: `tests/backend/icpy/test_clipboard_service.py`
  - System clipboard integration
  - Cross-client synchronization
  - Rich content handling

#### Step 5.3: Language Server Protocol (LSP) Integration Service
- Create `backend/services/lsp_service.py`
- Implement LSP client to communicate with language servers
- Support multiple language servers (TypeScript, Python, Rust, etc.)
- Provide code intelligence features (completion, diagnostics, hover, navigation)
- Integrate with file system service for real-time code analysis
- Cache LSP responses for improved performance
- **Integration Test**: `tests/backend/icpy/test_lsp_service.py`
  - LSP server lifecycle management
  - Code intelligence features
  - Multi-language support
  - Performance and caching

#### Step 5.4: AI Agent Integration Service
- Create `backend/services/ai_agent_service.py`
- Provide high-level API for AI tools to interact with workspace
- Support real-time file editing with immediate UI updates
- Enable AI tools to control terminal, file browser, and editor
- Add context management for AI agents (current active file, selection, etc.)
- Integrate with LSP service to provide code intelligence context to AI
- **Integration Test**: `tests/backend/test_ai_agent_service.py`
  - AI tool integration scenarios
  - Real-time editing and UI updates
  - Context management with LSP integration

### Phase 6: Extension Points for Future Features
**Goal**: Prepare architecture for planned rich text editor and advanced features

#### Step 6.1: Service Discovery and Registry
- Create `backend/core/service_registry.py`
- Implement service registration and discovery system
- Support service health monitoring and lifecycle management
- Add service dependency resolution and configuration management
- Enable dynamic service scaling and load balancing
- **Integration Test**: `tests/backend/test_service_registry.py`
  - Service registration and discovery
  - Health monitoring and dependency management
  - Dynamic service lifecycle

#### Step 6.2: Plugin System Foundation
- Create `backend/core/plugin_system.py`
- Define plugin interfaces and lifecycle management
- Support dynamic plugin loading and unloading
- Add plugin configuration and dependency management
- Integrate with service registry for plugin discovery
- **Integration Test**: `tests/backend/test_plugin_system.py`
  - Plugin lifecycle management
  - Dynamic loading and configuration
  - Service integration

#### Step 6.3: Authentication and Security Service
- Create `backend/services/auth_service.py`
- Implement authentication and authorization system
- Support multiple authentication methods (API keys, tokens, etc.)
- Add session management and permission-based access control
- Include security middleware for request validation and rate limiting
- **Integration Test**: `tests/backend/test_auth_service.py`
  - Authentication flows and session management
  - Permission-based access control
  - Security middleware functionality

#### Step 6.4: Content Management Service (Foundation)
- Create `backend/services/content_service.py`
- Provide abstract interface for different content types
- Support versioning and collaboration features
- Prepare for future rich text editor integration
- **Integration Test**: `tests/backend/test_content_service.py`
  - Content type handling
  - Versioning and collaboration

## Testing Strategy

### Unit Tests
- Test individual functions and classes in isolation
- Mock external dependencies and focus on business logic
- Emphasize edge cases and error conditions
- Target 90%+ code coverage for all services

### Integration Tests
- Test interactions between services via message broker
- Use real services with in-memory implementations
- Focus on happy paths and common error scenarios
- Test real-time event propagation and state synchronization

### End-to-End Tests
- Test complete user workflows across all interfaces
- Use real WebSocket connections and HTTP requests
- Test CLI commands with actual file system operations
- Validate AI tool integration scenarios

## Migration Strategy

### Backward Compatibility
- Maintain existing WebSocket and HTTP endpoints during transition
- Implement feature flags for gradual rollout
- Support both old and new protocols simultaneously
- Provide migration tools for existing data

### Incremental Deployment
1. Deploy message broker and protocol foundations (Phase 1)
2. Migrate services one by one (Phase 2)
3. Enhance API layer while maintaining compatibility (Phase 3)
4. Add real-time features (Phase 4)
5. Roll out advanced features (Phase 5)

### Rollback Plan
- Maintain old implementation alongside new services
- Support instant rollback at any phase
- Comprehensive monitoring and alerting
- Automated testing before each deployment

## Performance Considerations

### Optimization Targets
- Sub-100ms response time for file operations
- Real-time terminal I/O with minimal latency
- Support for 50+ concurrent WebSocket connections
- Efficient memory usage with connection pooling

### Monitoring and Metrics
- Service-level performance monitoring
- Real-time connection and event metrics
- Error rate and availability tracking
- Resource usage and scaling indicators

### Caching Strategy
- Multi-level caching for file operations and LSP responses
- Intelligent cache invalidation based on file changes
- Distributed caching support for multi-instance deployments
- Cache performance monitoring and optimization

### Load Balancing and Scaling
- Horizontal scaling support for multiple backend instances
- Load balancing based on service health and capacity
- Dynamic service scaling based on demand
- Connection pooling and resource optimization

## Future Extensibility

### Rich Text Editor Integration
- Content service foundation supports rich text documents
- Event-driven architecture enables real-time collaboration
- Plugin system allows custom rich text features
- AI integration enables smart content assistance

### AI Agent Framework Integration
- Service-oriented architecture supports AI tool integration
- Real-time state synchronization enables immediate feedback
- CLI interface allows external AI tools to control workspace
- Context management provides AI agents with workspace awareness
- LSP integration provides code intelligence context to AI agents for better assistance

### Code Intelligence and Developer Experience
- LSP integration provides modern IDE features (completion, diagnostics, navigation)
- Multi-language support through standard LSP protocol
- Real-time code analysis and error detection
- Enhanced AI agent capabilities with code context understanding
- Foundation for advanced features like refactoring and code generation

### Cross-platform Compatibility
- Full support for Linux, macOS, and Windows environments
- Cross-platform file system operations and path handling
- Terminal compatibility across different shells and operating systems
- Clipboard integration with native system clipboard on all platforms
- Environment-specific optimizations and configurations

### Multi-User Collaboration
- State synchronization service supports multiple users
- Event broadcasting enables real-time collaboration
- Workspace service supports user permissions and roles
- Conflict resolution handles concurrent edits

## Conclusion

This plan provides a comprehensive roadmap for creating a modern, modular backend architecture that maintains compatibility with the existing system while providing a solid foundation for future enhancements. The phased approach ensures incremental progress with thorough testing at each stage, while the event-driven architecture enables the real-time collaboration and AI integration features that are core to the project's vision.

The architecture is designed to support the three core components of the planned system: rich text editor, code editor + terminal, and AI agent integration, while maintaining the flexibility to adapt to future requirements without significant rewrites.
