# Changelog

All notable changes to the JavaScript Code Editor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Enhanced Multi-Layer Clipboard System**: Comprehensive clipboard solution bypassing browser security
  - Multi-layer clipboard service with automatic fallback hierarchy
  - Server-side system clipboard integration via file-based storage
  - Cross-platform support (Linux, macOS, Windows clipboard tools)
  - Visual notifications and real-time status indicators
  - Clipboard history management and persistence
  - React-compatible service with event emitters
  - Keyboard shortcuts (Ctrl+Shift+C/V) with user feedback
- **Simple Terminal Implementation**: Clean terminal component for testing and debugging
  - Minimal terminal based on ICUITerminalPanel.tsx
  - Direct WebSocket connection to ICPY backend
  - Backend clipboard API integration
  - Theme-aware styling and proper scrolling behavior
  - Connection status monitoring and error handling
- **Single-Port Architecture**: Unified server configuration
  - Backend serves both static files and API endpoints on single port
  - Environment-based configuration using .env variables
  - Dynamic WebSocket URL construction
  - Consistent port usage across frontend and backend

### Fixed
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
