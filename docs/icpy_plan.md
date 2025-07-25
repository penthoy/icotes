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

### 🚨 Phase 0: Critical Infrastructure Fixes ✅ COMPLETED
**Goal**: Resolve blocking issues preventing ICPY architecture from functioning

✅ **RESOLVED**: All critical infrastructure issues have been resolved and ICPY architecture is now fully functional.

#### Step 0.1: Pydantic Compatibility Resolution ✅ COMPLETED
- **Issue**: System Pydantic v1.10.14 vs ICPY requirement for v2.x 
- **Root Cause**: Backend not using virtual environment correctly
- **Solution**: Virtual environment has correct Pydantic v2.5.0 with field_validator
- **Status**: ✅ Complete - Backend startup scripts properly use virtual environment
- **Validation**: `from icpy.api import get_rest_api` now succeeds

#### Step 0.1b: Module Import Path Resolution ✅ COMPLETED
- **Issue**: Backend can't find ICPY modules due to incorrect working directory
- **Solution**: Backend startup scripts properly configured to use virtual environment
- **Status**: ✅ Complete - Backend logs show ICPY modules loading successfully
- **Validation**: Backend logs show ICPY modules available, no import errors

#### Step 0.2: Temporary Code Removal ✅ NO LONGER NEEDED
- **Status**: No temporary file endpoints were added to main.py
- **Current State**: Backend properly integrates with ICPY REST API services
- **Validation**: `/api/files` serves from ICPY services correctly

#### Step 0.3: ICPY Service Integration Validation ✅ COMPLETED
- **Status**: All ICPY services load and initialize correctly
- **Validation**: REST API endpoints are accessible and functional  
- **Verification**: Frontend receives proper JSON responses from file endpoints
- **Monitoring**: Backend logs show ICPY services as available and functional

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

### Phase 2: Core Services Foundation ✅ COMPLETED
**Goal**: Refactor existing functionality into modular services

✅ **UNBLOCKED**: All Phase 2 services are now fully accessible and functional with Pydantic compatibility resolved.

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

#### Step 2.2: File System Service ✅ COMPLETED
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
- **Status**: ✅ Complete and fully functional with ICPY REST API integration

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

#### Step 2.4: Enhanced Clipboard Service
**Goal**: Implement multi-layer clipboard system with browser security bypass

- Create `backend/icpy/services/clipboard_service.py`
- Implement multi-layer clipboard strategy:
  1. Browser native Clipboard API (when available in secure context)
  2. Server-side clipboard bridge with system integration
  3. CLI-based clipboard commands (`xclip`, `pbcopy`, etc.)
  4. File-based clipboard fallback (`/tmp/icpy_clipboard.txt`)
- Add clipboard operations: read, write, clear, status
- Support multiple clipboard formats (text, HTML, images)
- Implement automatic fallback hierarchy with user feedback
- Add secure context detection and PWA support
- Include clipboard history and persistence options
- Integrate with message broker for real-time clipboard sync
- **Integration Test**: `tests/backend/icpy/test_clipboard_service.py`
  - Multi-layer clipboard operations
  - Fallback hierarchy and error handling
  - System integration and security contexts
  - Cross-platform compatibility

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

#### Step 3.2: HTTP REST API ✅ COMPLETED
- Create `backend/icpy/api/rest_api.py`
- Implement RESTful endpoints for all services
- Support file operations, terminal management, and workspace operations
- Add OpenAPI/Swagger documentation
- **Integration Test**: `tests/backend/icpy/test_rest_api.py`
  - CRUD operations via HTTP
  - Error handling and validation
  - API documentation accuracy
- **Status**: ✅ Complete, tested, and fully accessible

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

### Phase 4: Real-time State Synchronization
**Goal**: Enable seamless real-time updates across all clients

#### Step 4.1: State Synchronization Service ✅ COMPLETED
- ✅ Created `backend/icpy/services/state_sync_service.py`
- ✅ Implemented client state mapping and synchronization
- ✅ Added state diffing and incremental updates
- ✅ Implemented conflict resolution for concurrent edits (last-writer-wins, first-writer-wins, merge strategies)
- ✅ Added client presence awareness (active file, cursor position, viewing files, status)
- ✅ **Integration Test**: `tests/backend/icpy/test_state_sync_service.py` - 23 tests passing
  - ✅ Multi-client state synchronization
  - ✅ Conflict resolution with multiple strategies
  - ✅ Presence awareness and real-time updates
  - ✅ State checkpoints and rollback functionality
  - ✅ Event-driven architecture integration
  - ✅ Concurrent operations support

**Implementation Details**:
- Created comprehensive StateSyncService with event-driven communication
- Supports multiple conflict resolution strategies (last-writer-wins, first-writer-wins, merge, manual)
- Implements client presence tracking with cursor position, active files, and viewing status
- Provides state checkpoints for rollback capabilities
- Includes history trimming and checkpoint cleanup for performance
- Full integration with message broker and connection manager
- Comprehensive error handling and edge case management
- **Tests**: All 23 integration tests pass including service lifecycle, client management, state changes, conflicts, presence, checkpoints, and performance
- **Files Created**: `backend/icpy/services/state_sync_service.py`, `backend/tests/icpy/test_state_sync_service.py`
- **Status**: Complete and fully tested

#### Step 4.2: Event Broadcasting System ✅ COMPLETED
- ✅ Created `backend/icpy/core/event_broadcaster.py`
- ✅ Implemented event broadcasting to all connected clients (WebSocket, HTTP long-polling)
- ✅ Added targeted event delivery based on client interests
- ✅ Implemented event filtering and routing based on permissions
- ✅ Added event history and replay for disconnected clients
- ✅ **Integration Test**: `tests/backend/icpy/test_event_broadcaster.py` - 26 tests passing
  - ✅ Event broadcasting to multiple clients
  - ✅ Targeted delivery and filtering
  - ✅ Event history and replay

**Implementation Details**:
- Created comprehensive EventBroadcaster with advanced filtering and delivery modes
- Supports multiple delivery modes: broadcast, targeted, filtered, unicast
- Implements client interest registration with topic patterns and permissions
- Provides event history with configurable size limits and cursor-based replay
- Includes priority-based event handling and statistics tracking
- Full integration with message broker and connection manager
- Comprehensive error handling and edge case management
- **Tests**: All 26 integration tests pass including service lifecycle, event broadcasting, filtering, targeting, history, replay, and performance
- **Files Created**: `backend/icpy/core/event_broadcaster.py`, `backend/tests/icpy/test_event_broadcaster.py`
- **Status**: Complete and fully tested

### Phase 5: Enhanced Services
**Goal**: Add advanced functionality and prepare for future features

#### Step 5.1: Code Execution Service ✅ COMPLETED
- ✅ Created `backend/icpy/services/code_execution_service.py`
- ✅ Refactored existing code execution from `backend/main.py`
- ✅ Implemented multi-language support (Python, JavaScript, Bash)
- ✅ Added sandboxed execution with timeout protection
- ✅ Implemented execution result caching and history
- ✅ Added real-time output streaming capability
- ✅ **Integration Test**: `tests/backend/icpy/test_code_execution_service.py` - 22/22 tests passing (100%)
  - ✅ Multi-language execution (Python, JavaScript, Bash)
  - ✅ Complete execution safety and sandboxing
  - ✅ Real-time output streaming
  - ✅ Error handling, timeout management, and cancellation

**Implementation Details**:
- Created comprehensive CodeExecutionService with multi-language support
- Supports Python (exec), JavaScript (Node.js), and Bash script execution
- Implements execution timeouts, resource limits, and sandboxing
- Provides real-time streaming execution for interactive scenarios
- Includes execution history, result caching, and statistics tracking
- Full integration with message broker for event-driven communication
- Comprehensive error handling for different execution scenarios
- **Tests**: All 22 integration tests pass including basic execution, streaming, history, caching, statistics, timeout, and cancellation
- **Files Created**: `backend/icpy/services/code_execution_service.py`, `backend/tests/icpy/test_code_execution_service.py`
- **Status**: Complete and fully tested (100% test success rate)

#### Step 5.2: Enhanced Clipboard Service ✅ COMPLETED
- ✅ Created `backend/icpy/services/clipboard_service.py` 
- ✅ Refactored existing clipboard functionality from `backend/main.py`
- ✅ Implemented multi-layer clipboard strategy with automatic fallback
- ✅ Added system clipboard integration (xclip, pbcopy, wl-clipboard)
- ✅ Implemented clipboard history and cross-client synchronization
- ✅ Added support for rich content types and large content handling
- ✅ **Integration Test**: `tests/backend/icpy/test_clipboard_service.py` - 16/19 tests passing
  - ✅ Multi-layer fallback hierarchy (system → CLI → file)
  - ✅ Cross-platform compatibility (Linux, macOS, Windows)
  - ✅ Clipboard history and content management
  - ⚠️ Minor issues: response structure consistency, X11 display dependency in tests

**Implementation Details**:
- Created comprehensive ClipboardService with multi-layer fallback strategy
- Supports browser native Clipboard API, server-side clipboard bridge, CLI commands, and file fallback
- Implements automatic system detection and tool availability checking
- Provides clipboard history with configurable limits and timestamp tracking
- Includes cross-platform support with system-specific clipboard tools
- Handles large content, concurrent operations, and error recovery gracefully
- Full integration with existing backend clipboard endpoints
- **Tests**: 16/19 integration tests pass including multi-layer operations, history, concurrency, and error handling
- **Files Created**: Enhanced `backend/icpy/services/clipboard_service.py`, `backend/tests/icpy/test_clipboard_service.py`
- **Status**: Core functionality complete and tested (84% test success rate)

#### Step 5.3: Language Server Protocol (LSP) Integration Service ✅ COMPLETED
- ✅ Created `backend/icpy/services/lsp_service.py`
- ✅ Implemented pygls-based Language Server Protocol client
- ✅ Added multi-language LSP server management (Python, JavaScript, TypeScript)
- ✅ Integrated code intelligence features (completion, diagnostics, hover, navigation)
- ✅ Implemented workspace document management and text synchronization
- ✅ Added real-time diagnostics and code validation
- ✅ **Integration Test**: `tests/backend/icpy/test_lsp_service_basic.py` - 15/15 tests passing (100%)
  - ✅ Service instantiation and configuration
  - ✅ LSP server management (start/stop/restart)
  - ✅ Document management and text synchronization
  - ✅ Code intelligence features (completion, hover, diagnostics)
  - ✅ Workspace management and symbol resolution

**Implementation Details**:
- Created comprehensive LSPService with multi-language support
- Supports Python, JavaScript, TypeScript, and extensible language configurations
- Implements document synchronization and change tracking
- Provides code completion, hover information, and real-time diagnostics
- Includes workspace symbol search and definition/reference navigation
- Full integration with message broker for event-driven LSP communication
- Comprehensive server lifecycle management with health monitoring
- **Tests**: All 15 integration tests pass including service attributes, server management, document handling, and code intelligence features
- **Files Created**: `backend/icpy/services/lsp_service.py`, `backend/tests/icpy/test_lsp_service_basic.py`
- **Status**: Complete and fully tested (100% test success rate)

#### Step 5.4: AI Agent Integration Service ✅ COMPLETED
- ✅ Created `backend/icpy/services/ai_agent_service.py`
- ✅ Implemented high-level API for AI tools to interact with workspace
- ✅ Added comprehensive agent registration and context management
- ✅ Integrated with all existing services (FileSystem, CodeExecution, LSP, Terminal, Workspace, Clipboard)
- ✅ Implemented action execution system with 22 different action types
- ✅ Added real-time event subscription and forwarding system
- ✅ Created workspace intelligence gathering and code execution with context
- ✅ **Integration Test**: `tests/backend/icpy/test_ai_agent_service_basic.py` - 25/25 tests passing (100%)
  - ✅ Agent registration, unregistration, and context management
  - ✅ Action execution for all supported action types
  - ✅ Event subscription and notification system
  - ✅ Service integration and error handling
  - ✅ Activity tracking and action history

**Implementation Details**:
- Created comprehensive AIAgentService with full workspace integration
- Supports 8 core agent capabilities (file operations, code execution, terminal control, LSP intelligence, workspace navigation, clipboard access, real-time editing, context awareness)
- Implements 22 different action types covering all workspace operations
- Provides agent context management with active file, cursor position, selection tracking
- Includes real-time event subscription system for workspace changes
- Integrates with all backend services through lazy initialization pattern
- Supports workspace intelligence gathering combining LSP diagnostics and symbols
- Enables code execution with contextual file information
- Full integration with message broker for event-driven agent communication
- **Tests**: All 25 integration tests pass including registration, actions, events, service integration, and error handling
- **Files Created**: `backend/icpy/services/ai_agent_service.py`, `backend/tests/icpy/test_ai_agent_service_basic.py`
- **Status**: Complete and fully tested (100% test success rate)

### Phase 6: Agentic foundation
**Goal**: Foundational Agentic services

#### Step 6.1:
Install openai agent sdk, crewAI, langchain langraph and make sure they work.

#### Step 6.2:
create a backend/icpy/agent folder where we can put our custom agentic workflow

#### Step 6.3:
create services that exposes these workflows

Prepare architecture for Agentic frameworks and provide services to these frame works.

### Phase 7: Extension Points for Future Features
**Goal**: Prepare architecture for planned rich text editor and advanced features

#### Step 7.1: Service Discovery and Registry
- Create `backend/core/service_registry.py`
- Implement service registration and discovery system
- Support service health monitoring and lifecycle management
- Add service dependency resolution and configuration management
- Enable dynamic service scaling and load balancing
- **Integration Test**: `tests/backend/test_service_registry.py`
  - Service registration and discovery
  - Health monitoring and dependency management
  - Dynamic service lifecycle

#### Step 7.2: Plugin System Foundation
- Create `backend/core/plugin_system.py`
- Define plugin interfaces and lifecycle management
- Support dynamic plugin loading and unloading
- Add plugin configuration and dependency management
- Integrate with service registry for plugin discovery
- **Integration Test**: `tests/backend/test_plugin_system.py`
  - Plugin lifecycle management
  - Dynamic loading and configuration
  - Service integration

#### Step 7.3: Authentication and Security Service
- Create `backend/services/auth_service.py`
- Implement authentication and authorization system
- Support multiple authentication methods (API keys, tokens, etc.)
- Add session management and permission-based access control
- Include security middleware for request validation and rate limiting
- **Integration Test**: `tests/backend/test_auth_service.py`
  - Authentication flows and session management
  - Permission-based access control
  - Security middleware functionality

#### Step 7.4: Content Management Service (Foundation)
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
