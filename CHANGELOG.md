# Changelog

All notable changes to the JavaScript Code Editor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### August 2025 - Enhanced Component Cleanup & Architecture Optimization

- **ICUI Enhanced Component Cleanup**: Major codebase cleanup removing "Enhanced" prefixes and consolidating component architecture
  - **Component Consolidation**: Removed alternative implementations (`ICUITerminalPanelFromScratch`, `ICUIEditorPanelFromScratch`) and backup files (`ICUITerminalEnhanced_backup`, `ICUIEnhancedEditorPanelOld`)
  - **Primary Component Migration**: Main application now uses clean `ICUILayout` instead of `ICUIEnhancedLayout`
  - **Export Reorganization**: Clean components prioritized as primary exports with deprecated Enhanced versions for backward compatibility
  - **Service Architecture Optimization**: Discovered and preserved optimal pattern where Enhanced services are implementations with clean API facades
  - **Final Consolidation (Phase 6)**: Deprecated `ICUIEnhancedLayout` (renamed to `_deprecated.tsx`) after migrating all integration tests to use clean `ICUILayout`
  - **Build Stability**: All changes maintained zero breaking changes with full backward compatibility
  - **Reduced Maintenance**: Eliminated 5 files (4 removed + 1 deprecated) while preserving all functionality and achieving clean architecture

#### July 2025 - Major Integration and Backend Fixes

- **Pytest Warnings Cleanup**: Reduced pytest warnings from 1599 to 33 (98% reduction) by adding pytest configuration filters for external dependencies and fixing datetime.utcnow() deprecation warnings.

- **ICPY Phase 6.5: Custom Agent Integration Complete**: Unified chat service integration for custom agents with real-time streaming through `/ws/chat` endpoint using START→CHUNKS→END protocol with full database persistence.

- **Debug Log Cleanup & Production Readiness**: Comprehensive cleanup of console.log statements from frontend/backend components and removed chat.db from git tracking for production readiness.

- **ICPY Plan Steps 6.1, 6.2, & 6.3 Completion**: Completed all major ICPY agentic framework foundation steps with 56 passing tests, full workflow infrastructure, and agent service layer operational.

- **Custom Agent System Implementation**: Complete custom agent system with dropdown interface, streaming support, fixed OpenAIDemoAgent import issues, and full chat history persistence.

- **Main.py Backend Refactoring**: Comprehensive backend cleanup reducing main.py from 1441 to 958 lines, removed legacy endpoints, organized code into functions.

- **UI Component Fixes & Enhancements**: Fixed panel tab persistence, drag/drop infinite loops, terminal arrow key navigation, custom agent dropdown implementation.

- **Custom Agent Architecture Abstraction**: Implemented CustomAgentBase abstract class with unified chat interface and agent registry system.

- **ICUIChat.tsx Component Implementation**: Created new ICUI chat component with full theme support, WebSocket integration, replaced ICUIChatPanel.

- **Streaming Chat & ICPY Phase 6 Complete**: Fixed duplicate message handling in streaming responses, completed icpy_plan.md steps 6.1-6.4 for production-ready agentic infrastructure.

- **Framework Installation & Validation**: Installed and validated OpenAI SDK, CrewAI, LangChain/LangGraph with unified interface and comprehensive testing.

- **Simple Components & Integration Testing**: Created simple components for testing, implemented smart domain detection for Cloudflare tunnel compatibility.

- **Explorer & Home Route Enhancements**: Implemented VS Code-like explorer with tree folder expansion, real-time file system monitoring, migrated inthome.tsx to home.tsx.

- **Framework Services & Theme Fixes**: Created notification service and backend client abstractions, fixed terminal/editor theme color consistency.

- **Editor Bug Fixes & Tab Management**: Fixed critical tab switching without reload, cursor positioning bugs, proper scrollbar implementation.

- **Debug Log Cleanup & Production Readiness Preparation**: Comprehensive cleanup of all phased debug logs and codebase preparation for production deployment. Removed debug logs from backend streaming files and frontend chat components, removed chat.db from git tracking, added WebSocket message type support, and verified build success. Codebase is now production-ready with clean logs, proper database management, and resolved frontend warnings.

- **BackendConnectedEditor Cursor Positioning Bug Fix**: Fixed critical cursor positioning issue where typing caused cursor to jump to beginning instead of staying at current position. Root cause was stale closure issues in CodeMirror updateListener and unnecessary editor recreations. Applied fixes following the working ICUIEnhancedEditorPanel pattern including editor recreation logic fixes, updateListener closure fixes, content reference tracking, and content update effect improvements.

- **Integration Plan Phase 2.4 - Home.tsx Rewrite and ICPY Preparation**: Successfully completed rewrite of home.tsx for ICPY integration. Copied original home.tsx to tests/integration/inthome.tsx and refactored for backend integration readiness. Cleaned up components, simplified backend state management with graceful fallbacks, and maintained existing integration while preparing for future ICPY backend connection.

- **Comprehensive Integration Test Environment**: Implemented three-panel integration test environment with BackendConnectedEditor component, ComprehensiveIntegrationTest component providing unified IDE-like interface, IntegrationTestControls with comprehensive test automation, and full ICPY backend connectivity. Accessible at `/integration` with complete IDE experience.

- **Event Broadcasting System Implementation**: Advanced Event Broadcasting System with priority-based broadcasting, targeted delivery modes (broadcast, multicast, unicast), advanced event filtering with permissions, client interest management, event history and replay functionality, and seamless integration with MessageBroker and ConnectionManager.

- **ICUI Layout Menu Implementation**: Comprehensive LayoutMenu component with layout templates and presets, custom layout management with localStorage integration, panel creation options for all panel types, layout reset functionality, import/export capabilities, and full ICUILayoutStateManager integration with dark theme support.

- **State Synchronization Service Implementation**: Comprehensive State Synchronization Service with multi-client state mapping, state diffing and incremental updates, conflict resolution strategies, client presence awareness with cursor tracking, state checkpoints and rollback functionality, and event-driven communication via message broker.

- **ICUI File Menu Implementation**: Comprehensive FileMenu component with file operations (New, Open, Save, Save As, Close), recent files tracking with localStorage persistence, project management features, settings access, keyboard shortcuts support, and full FileService integration with dark theme support.

- **Critical Backend Issues Resolution**: Fixed all critical backend issues including Pydantic version compatibility resolution, ICPY modules loading successfully in virtual environment, removal of temporary fallback code from backend/main.py, and proper ICPY REST API integration restoration. Backend now shows "icpy modules loaded successfully" and all services initialize correctly.

- **ICUI Top Menu Bar Implementation**: Created complete dropdown menu system with File, Edit, View, and Layout menus, keyboard shortcut support, menu customization, submenu support, ICUI theming integration, and notification system integration.

- **Service Framework Enhancements**: Implemented File Management Service with comprehensive file CRUD operations, Theme Detection and Management Service with MutationObserver-based automatic theme detection, service naming cleanup removing redundant ICUI prefixes, and notification service integration with toast notifications.

- **Enhanced Multi-Layer Clipboard System (PARTIAL)**: Comprehensive clipboard solution bypassing browser security
  - Multi-layer clipboard service with automatic fallback hierarchy (Native API → Server → CLI → File)
  - Server-side system clipboard integration via file-based storage and CLI tools
  - Cross-platform support (Linux xclip/xsel, macOS pbcopy, Windows clip)
  - Visual notifications and real-time status indicators showing active clipboard method
  - Clipboard history management and persistence across sessions
  - React-compatible service with event emitters and TypeScript interfaces
  - Keyboard shortcuts (Ctrl+Shift+C/V) with user feedback and error handling
  - Enhanced backend endpoints: `/clipboard/status` and `/clipboard/clear`
  - Note: System clipboard bypass works via file storage but needs display/X11 for full cross-app access
- **Simple Terminal Implementation**: Clean terminal component for testing and debugging
  - Minimal terminal based on ICUITerminalPanel.tsx with direct WebSocket connection
  - Backend clipboard API integration with copy/paste keyboard shortcuts
  - Theme-aware styling, proper scrolling behavior, and connection monitoring
  - Accessible at `/simple-terminal` route for isolated testing
  - Error handling, reconnection logic, and responsive terminal sizing
- **Simple Explorer Implementation**: Clean file explorer component for testing and debugging
  - Minimal file explorer based on BackendConnectedExplorer.tsx with direct REST API connection
  - File system operations (create file/folder, delete, navigate directory tree)
  - Theme-aware styling, connection status monitoring, and error handling
  - Accessible at `/simple-explorer` route for isolated testing
  - Real-time directory contents loading and visual feedback for all operations
  - Fixed API endpoint issues: uses `/health` instead of missing `/api/status`
  - Respects VITE_WORKSPACE_ROOT environment variable for workspace root
  - Fixed API URL configuration and response parsing for proper file display
  - Full CRUD file operations working with ICPY backend file system service
- **File Explorer Integration**: Backend-connected file explorer component
  - Real-time directory tree loading from ICPY backend filesystem service
  - File and folder operations (create, delete, navigate) via backend API
  - Connection status monitoring with auto-refresh after operations
  - Seamless integration with IntegratedHome test environment
- **Integration Test Environment**: Comprehensive test environment with backend connectivity
  - Debug integration component for connectivity troubleshooting
  - Integration test accessible at `/integration` route with status monitoring
  - Manual testing environment for backend component integration
  - TypeScript compilation fixes and proper error handling
- **Backend State Synchronization**: Infrastructure for ICUI-ICPY integration
  - Backend context provider for application-wide backend access
  - Real-time workspace state synchronization with bi-directional updates
  - Connection monitoring, auto-reconnection, and local state persistence
  - Type-safe backend communication with comprehensive error handling
- **Single-Port Architecture**: Unified server configuration
  - Backend serves both static files and API endpoints on single port
  - Environment-based configuration using .env variables
  - Dynamic WebSocket URL construction and consistent port usage

### Fixed
- **Simple Explorer API Issues**: Fixed connection and endpoint issues ✅ RESOLVED
  - Backend team confirmed all REST API endpoints are fully functional when run in virtual environment
  - Updated simple-explorer to use correct `/api/health` and `/api/files` endpoints  
  - Fixed VITE_API_URL configuration to use full URL from environment
  - Added proper VITE_WORKSPACE_ROOT environment variable support
  - Confirmed full file system operations working: create, read, delete, list directories
  - Successfully tested with backend running in virtual environment per TICKET_RESPONSE.md
  - Simple Explorer now fully functional at `/simple-explorer` route
- **Backend Configuration**: Fixed hardcoded port issues
  - Backend now properly uses .env configuration (PORT, BACKEND_HOST, etc.)
  - Removed hardcoded port 8888 references
  - Single-port solution implemented using port 8000
- **Terminal Double Echo**: Removed debug logging causing character duplication
  - Clean terminal output without debug noise
  - Proper backend-only echo handling
- **ICUI Enhanced Editor Implementation**: Complete editor system overhaul
  - New ICUIEnhancedEditorPanel.tsx combining best features from all implementations
  - Framework abstraction with syntaxHighlighting.ts utility functions
  - From-scratch editor rewrite eliminating legacy dependencies
  - Full tabs functionality with file switching, close buttons, and creation
  - Complete ICUI framework integration using CSS variables
  - Keyboard shortcuts (Ctrl+S to save, Ctrl+Enter to run)
- **Advanced Theme System**: Comprehensive theme improvements
  - Fixed CodeEditor background issues in dark themes
  - 5 distinct themes: GitHub Dark/Light, Monokai, One Dark, VS Code Light
  - Comprehensive CSS variables infrastructure
  - Theme selection dropdown in test application
- **UI/UX Improvements**: Layout system enhancements
  - Panel footer attachment fix for browser resize handling
  - Proper height constraints with maxHeight: '100vh'
  - Enhanced layout container structure

### Fixed
- **Critical Panel Management Bug**: Fixed disappearing panels during tab switching
  - Separated panel initialization from content updates
  - Fixed infinite tab switching loops
  - Preserved dynamic panel state across tab switches
- **Theme System Issues**: Multiple theme-related fixes
  - Fixed active tab styling with proper visual hierarchy
  - Fixed code editor empty areas using theme CSS variables
  - Improved scrollbar readability (12px size, theme-aware colors)
  - Fixed panel area theming with consistent CSS variables
- **CodeEditor Background & Divider**: Fixed white background issues in dark themes
  - Enhanced panel integration with theme-aware background containers
  - Dimmed divider colors for better dark theme experience
  - Consistent dark experience across all editor areas

### Changed
- **Editor Architecture**: Replaced legacy editor with dependency-free implementation
  - No dependencies on problematic CodeEditor.tsx component
  - Simplified CodeMirror integration with essential extensions only
  - ICUI theme native design using CSS variables from the start
- **Layout System**: Enhanced layout container and frame structure
  - Updated ICUIEnhancedLayout and ICUIFrameContainer flex structure
  - Panels and footer now scale together maintaining proper attachment

## [1.1.0] - 2024-12-19

### Added
- **ICUI Framework Polish**: Complete cleanup and finalization of ICUI terminal panel
  - Finalized ICUITerminalPanel as the single reference implementation
  - Removed all legacy terminal panel versions (V2, V3)
  - Clean export structure with proper ICUI panel integration
- **Codebase Cleanup**: Comprehensive cleanup of development artifacts
  - Removed debug console.log statements from all ICUI components
  - Cleaned up development test scripts that are no longer needed
  - Preserved production-appropriate error and warning logging
  - Maintained development-only debug sections with proper NODE_ENV guards
- **Documentation Updates**: Updated project documentation to reflect current state
  - Updated roadmap.md with completed terminal implementation
  - Updated Working.md with recently finished features
  - Comprehensive changelog documentation

### Fixed
- Debug console.log statements in ICUITerminalPanel, ICUIEditorPanel, ICUIExplorerPanel
- Debug console.log in ICUILayoutPresetSelector export functionality
- Removed unnecessary debug borders and development overlays

### Changed
- ICUITerminalPanelV3 renamed to ICUITerminalPanel as single reference implementation
- Cleaned up build output to be production-ready
- Streamlined ICUI component structure for maintainability

### Removed
- Legacy ICUITerminalPanelV2 and ICUITerminalPanelV3 files
- Development test scripts: test-terminal-scroll.py, test-terminal-scroll.sh, test-websocket.py, test-terminal.sh
- Debug console.log statements and development artifacts

## [1.0.0] - 2024-12-18

### Added
- Real terminal with PTY support using xterm.js and WebSocket communication
- Python language support as default with syntax highlighting
- VSCode-like file explorer sidebar with resizable panel
- FastAPI backend with WebSocket support for real-time communication
- Flexible UI panel system with collapse/expand and maximize functionality
- Multi-tab terminal system with closable tabs
- Vertical resizable terminal/output panel
- Comprehensive system architecture documentation

### Fixed
- Terminal connection and WebSocket communication issues
- Terminal boundary detection and scrolling problems
- Panel disappearing when arrow buttons are clicked
- Cursor disappearing issue in code editor
- Output panel layout positioning
- Frontend-backend connection problems
- Production frontend serving and static file handling
- Development environment script consistency

### Changed
- Updated development script to single-port architecture
- Enhanced port configuration for flexible deployment
- Improved terminal layout and scrolling behavior
- Streamlined deployment process with unified port usage

### Removed
- Tempo-specific code and dependencies cleanup
- Unused development artifacts and configurations

## [4.0.0] - 2025-07-08

### Added
- ICUITerminalPanel reference implementation with WebSocket connectivity
- ICUI Framework Phase 4 specialized panel implementations
- ICUIEditorPanel with file tabs and multi-language support  
- ICUIExplorerPanel with file tree operations and toolbar
- Dark theme support with real-time switching for better IDE experience
- RequestAnimationFrame batching for CodeEditor updates
- Enhanced terminal configuration with 2000-line scrollback

### Fixed
- Editor freezing issues through optimized update handling
- Panel content overflow problems with proper CSS scrolling
- Terminal scrolling problems by removing manual viewport manipulation
- Terminal container sizing and initialization issues
- All panels now scroll properly when content exceeds bounds

### Changed
- Updated ICUI panel area CSS to allow proper scrolling (overflow: auto)
- Enhanced terminal container sizing with multiple fit retry attempts
- Improved CodeEditor update listener with useCallback optimization
- Framework version updated to v4.0.0 (Phase 4 complete)

### Removed
- Legacy ICUITerminalPanelV2 and V3 versions for clean codebase
- Manual viewport manipulation that conflicted with xterm.js

---
*Last updated: July 8, 2025*
