# JavaScript Code Editor - Project Roadmap

## Project Overview
A web-based JavaScript code editor built with React, CodeMirror 6, and modern web technologies. The goal is to create a powerful, user-friendly code editor with real-time execution capabilities.

## In Progress
(No current tasks)

## Failed/Blocked Tasks

### Terminal Clipboard Implementation (FAILED)
- **Issue**: Terminal copy/paste functionality not working despite multiple implementation attempts
- **Attempts Made**: 
  1. Context menu with clipboard addon
  2. Auto-copy on selection with context menu
  3. Simplified keyboard shortcuts only
- **Root Cause**: Browser security restrictions prevent clipboard API access in current development environment
- **Status**: BLOCKED - requires HTTPS environment or alternative technical approach
- **Documentation**: See `docs/failed_context_imp.md` for detailed post-mortem
- **Recommendation**: Deprioritize until technical solution is found

## Future task
-- UI issues
- [] Terminal highlight white

-- Bug Fix:
- [] Fix panel flickering issue

-- api backend
- [] separate terminal code from main into terminal.py
- [] create an api layer between the front end and backend.
- [] This api layer can also be used in the comand line which also have hooks to the UI to do things like open a file in editor or have AI assistant use tools to edit file etc.
- api feature: detect what view is active so that the AI can have the correct context when you talk to it, it saves the state of the
- we'll add these endpoints later, but first we need to create a design document named api_design.md in docs folder and wait for me to review/edit it before proceed with building this layer.

-- Later
A Panel installer,
maya style code executor.

## Recently Finished

### December 2024 - Terminal Cleanup & Restoration
- **Terminal Restored to Clean State** ✅
  - **Issue**: Terminal contained non-functional clipboard code after failed implementation attempts
  - **Solution**: Restored terminal to clean, lean state while preserving enhanced features
  - **Implementation**:
    - Removed all clipboard-related imports (`@xterm/addon-clipboard`)
    - Removed all clipboard event handlers and state management
    - Removed all context menu code and UI components
    - Removed all keyboard shortcuts for copy/paste
    - Removed all auto-copy functionality
    - Uninstalled unused `@xterm/addon-clipboard` package
    - Preserved enhanced theming and scrolling fixes
    - Preserved local echo functionality for responsive typing
    - Preserved WebSocket connectivity and resize handling
  - **Result**: Clean, functional terminal with enhanced theming but no clipboard functionality
  - **Key Features Preserved**:
    - Enhanced theme detection and switching
    - Proper scrolling behavior (code-server pattern)
    - Local echo for instant character feedback
    - WebSocket connectivity to backend
    - Responsive resize handling
    - ICUI CSS variable integration

### December 2024 - Terminal Clipboard Implementation Attempts (FAILED)
- **Terminal Copy/Paste Implementation** ❌
  - **Issue**: Multiple attempts to implement terminal clipboard functionality failed
  - **Attempts Made**: 
    1. Context menu with clipboard addon
    2. Auto-copy on selection with right-click menu
    3. Simplified keyboard shortcuts only approach
  - **Root Cause**: Browser security restrictions prevent clipboard API access in development environment
  - **Technical Details**:
    - Added `@xterm/addon-clipboard` package (non-functional)
    - Implemented context menu UI with copy/paste options (showed but didn't work)
    - Added auto-copy on selection using `onSelectionChange` (blocked by security)
    - Added keyboard shortcuts Ctrl+Shift+C/V (blocked by security)
    - Added fallback using `document.execCommand` (also blocked)
  - **Code Changes Made**:
    - Added then removed context menu state management
    - Added then removed clipboard event handlers
    - Added then removed context menu UI components
    - Multiple iterations of clipboard integration attempts
  - **Status**: FAILED - All implementations blocked by browser security restrictions
  - **Documentation**: Created `docs/failed_context_imp.md` with detailed post-mortem
  - **Recommendation**: Requires HTTPS environment or alternative technical approach

### December 2024 - Development UI Cleanup
- **Debug Overlay Removal** ✅
  - **Issue**: Black debug information boxes appeared in development mode, cluttering the UI
  - **Solution**: Removed development-only debug overlays from ICUI components
  - **Implementation**:
    - Removed debug info from `ICUIFrameContainer.tsx` (frame size, viewport, borders info)
    - Removed debug info from `ICUISplitPanel.tsx` (split percentage, dragging state info)
    - Removed debug info from `ICUILayoutPresetSelector.tsx` (history length, presets info)
    - Maintained clean development experience while preserving error logging
  - **Result**: Clean, professional UI in development mode without debug overlays

### December 2024 - Terminal Context Menu Implementation
- **Terminal Copy and Paste Context Menu** ✅
  - **Issue**: Terminal lacked right-click context menu functionality for copy and paste operations
  - **Solution**: Implemented comprehensive context menu system with clipboard integration
  - **Implementation**:
    - Added `@xterm/addon-clipboard` package for system clipboard access
    - Created context menu state management with `ContextMenuState` interface
    - Added right-click event handler (`handleContextMenu`) to detect selection state
    - Implemented copy functionality that uses `terminal.getSelection()` and `navigator.clipboard.writeText()`
    - Implemented paste functionality that uses `navigator.clipboard.readText()` and sends to WebSocket
    - Added context menu UI with proper theming (dark/light mode support)
    - Context menu shows "Copy" option only when text is selected
    - Context menu always shows "Paste" option for pasting clipboard content
    - Added proper event cleanup and click-outside-to-close functionality
    - Styled context menu with hover effects and theme-aware colors
  - **Key Features**:
    - Right-click on highlighted text shows copy option
    - Right-click anywhere shows paste option
    - Proper clipboard integration using modern Web APIs
    - Theme-aware styling matching terminal appearance
    - Smooth hover effects and proper UX interactions
  - **Result**: Users can now right-click in terminal to copy selected text and paste clipboard content

### December 2024 - Panel Tab Color Fix & Drag & Drop Implementation
- **Panel Tab Color Scheme Fix** ✅
  - **Issue**: Panel tabs had reversed colors compared to editor tabs (active tabs were darker, inactive tabs were lighter)
  - **Solution**: Updated panel tab color scheme to match editor tabs
  - **Implementation**:
    - Modified `ICUITabContainer.tsx` to use `var(--icui-bg-tertiary)` for active tabs and `transparent` for inactive tabs
    - Updated CSS in `icui-panel-area.css` and `icui-themes.css` to match the new color scheme
    - Applied consistent color scheme across all theme variants (light, dark, and custom themes)
  - **Result**: Panel tabs now have the same visual hierarchy as editor tabs - active tabs are lighter and more prominent

- **Draggable Panel Tabs Implementation** ✅
  - **Issue**: Panel tabs could not be reordered within their areas
  - **Solution**: Added complete drag and drop functionality for panel tab reordering
  - **Implementation**:
    - Added `handlePanelReorder` function to `ICUIEnhancedLayout.tsx` to handle panel reordering within areas
    - Updated all `ICUIEnhancedPanelArea` instances to include `onPanelReorder` prop
    - Leveraged existing drag and drop infrastructure in `ICUITabContainer` component
    - Maintained existing cross-area panel movement functionality
  - **Result**: Users can now drag and drop panel tabs to reorder them within the same area

- **Draggable Editor Tabs Implementation** ✅
  - **Issue**: Editor file tabs could not be reordered
  - **Solution**: Added drag and drop functionality for editor file tabs
  - **Implementation**:
    - Added `onFileReorder` and `enableDragDrop` props to `ICUIEnhancedEditorPanel` interface
    - Implemented drag and drop handlers (`handleDragStart`, `handleDragOver`, `handleDrop`) in editor panel
    - Added `handleFileReorder` function in home component to manage file array reordering
    - Updated all editor panel instances to enable drag and drop functionality
    - Added proper drag attributes (`draggable`, `onDragStart`, `onDragOver`, `onDrop`) to tab elements
  - **Result**: Users can now drag and drop editor file tabs to reorder them

### December 2024 - Terminal Scrolling Fix Implementation
- **Terminal Scrolling Issue Resolution** ✅
  - **Issue**: Terminal panels showed black areas instead of scrollable content when commands produced large outputs (e.g., `history` command)
  - **Root Cause**: Fundamental mismatch between xterm.js viewport sizing and container layout, preventing proper scrollbar display
  - **Solution**: Complete rewrite of terminal implementation based on code-server analysis
  - **Implementation**: 
    - Created `ICUITerminalPanelFromScratch.tsx` with proper code-server patterns
    - Added `icuiTerminaltest.tsx` integration test component (accessible at `/icui-terminal-test`)
    - Used proper xterm.css viewport classes with `overflow-y: scroll` on `.xterm-viewport`
    - Implemented FitAddon with correct initialization order (open terminal BEFORE fitting)
    - Added ResizeObserver for dynamic container size changes
    - Applied critical CSS for viewport scrolling control
  - **Key Changes**:
    - Imported `@xterm/xterm/css/xterm.css` first before custom CSS
    - Container has explicit height constraints with `overflow: hidden`
    - Let xterm.js handle scrolling internally through `.xterm-viewport` element
    - Removed conflicting overflow properties from terminal wrapper
    - Added proper resize handling with debounced updates
    - Synchronized frontend/backend PTY dimensions via WebSocket
    - **Local Echo Fix**: Added proper local echo for instant character feedback
      - Printable characters (ASCII 0x20-0x7E) are echoed locally for instant feedback
      - Backspace/Delete handled locally with proper cursor movement
      - Enter/Return resets typed character count for new lines
    - **Enhanced Terminal Update**: Applied all fixes to ICUIEnhancedTerminalPanel
      - Merged all scrolling fixes into the original enhanced terminal component
      - Preserved enhanced theming with ICUI CSS variables and advanced color support
      - Maintained theme detection and switching capabilities
      - Both terminals now have identical scrolling behavior while enhanced keeps extra features
  - **Testing**: Available at `/icui-terminal-test` route for isolated testing
  - **Status**: Both scrolling and local echo working correctly in both terminal components

### December 2024 - Terminal Character Lag Fix
- **Backend Terminal Latency Optimization** ✅
  - **Root Cause**: Fixed 50ms character lag caused by slow polling timeout in `select.select()`
  - **Solution**: Reduced `select()` timeout from 50ms to 1ms for maximum responsiveness
  - **Additional Optimizations**:
    - Reduced async sleep from 10ms to 1ms when no data is available
    - Reduced write operation backoff from 10ms to 1ms for BlockingIOError handling
    - Optimized PTY configuration: Set `VMIN=1` for immediate character processing
    - Enhanced comments and documentation for terminal performance settings
  - **Impact**: Eliminated noticeable lag when typing characters in terminal
  - **Performance Trade-off**: Slightly increased CPU usage for dramatically improved responsiveness

### December 2024 - Previous Terminal Performance Optimization
- **Backend Performance Optimization** ✅
  - Increased `select()` timeout from 1ms to 50ms for efficient polling
  - Doubled buffer size from 4KB to 8KB for better throughput
  - Reduced async sleep time from 1ms to 10ms to lower CPU usage
  - Improved write operation backoff timing for smoother performance
  - Eliminated tight polling loops that were causing high CPU usage
- **Frontend Performance Optimization** ✅
  - Fixed terminal recreation issue on theme changes in ICUIEnhancedTerminalPanel
  - Separated terminal initialization from theme updates for better performance
  - Added debounced theme detection (50ms) to prevent rapid theme changes
  - Preserved terminal state and WebSocket connection during theme switches
  - Eliminated unnecessary terminal disposal and recreation cycles
- **Overall Performance Improvements** ✅
  - Reduced terminal response latency while maintaining responsiveness
  - Significantly lowered CPU usage during terminal operations
  - Improved terminal stability during theme changes
  - Enhanced WebSocket connection efficiency
  - Better memory management with optimized terminal lifecycle

### December 2024 - ICUI Base Layout Components & Header/Footer Framework
- **ICUI Base Header Component** ✅
  - Created `ICUIBaseHeader.tsx` with comprehensive header functionality
  - Includes File and Layout menu system with dropdown menus
  - File menu: New, Open, Save, Save As, Exit with proper separators
  - Layout menu: H Layout, IDE Layout, Reset Layout options
  - Theme switcher with full theme support
  - Layout action buttons integrated into menu system (removed from header)
  - Compact header design (3px vertical padding, 28px minimum height)
  - Micro-sized logo (h-4) and properly-sized menu buttons (px-3 py-1, text-sm) for optimal balance
  - Fully extensible with custom menu items and actions
- **ICUI Base Footer Component** ✅
  - Created `ICUIBaseFooter.tsx` with status bar functionality
  - Connection status indicator with color-coded status
  - File statistics display (file count, modified count)
  - Theme information display
  - Compact design (4px vertical padding, 28px minimum height)
  - Extensible with custom status items
- **Enhanced Layout Component** ✅
  - Created `Layout.tsx` in src/components that inherits from base classes
  - Provides complete framework for header and footer with advanced features
  - Integrates with application state (files, themes, connection status)
  - Handles menu actions and file operations
  - Supports layout switching and theme management
  - Updated home.tsx to use new Layout component
- **Framework Integration** ✅
  - Added components to ICUI index.ts exports
  - Proper TypeScript interfaces and type exports
  - Clean inheritance pattern demonstration
  - Maintains backward compatibility with existing code

### December 2024 - Brand Update & Visual Identity
- **Complete Brand Rename** ✅
  - Renamed application from "iLabors Code Editor" to "icotes" across all files
  - Updated README.md, documentation, shell scripts, and backend API titles
  - Changed HTML document title to "icotes" in index.html
- **Favicon Update** ✅
  - Replaced vite.svg with logo.svg as the favicon
  - Updated index.html to use `/logo.svg` instead of `/vite.svg`
  - Removed old vite.svg file from public directory
- **Logo Integration** ✅
  - Replaced "JavaScript Code Editor" text with logo image in header
  - Updated home.tsx to use `/logo.png` image instead of text title
  - Maintained proper responsive design with appropriate logo height

### December 2024 - ICUI Framework Migration & Home Component Rewrite
- **Archived Pre-ICUI Components** ✅
  - Created archived folder under `src/components/archived/`
  - Moved legacy components (CodeEditor, Terminal, XTerminal, OutputTerminalPanel, etc.) to archived folder
  - Components were pre-ICUI framework and duplicated functionality now available in ICUI framework
- **New Production-Ready Home Component** ✅
  - Rewrote home.tsx based on ICUITestEnhanced.tsx with production-ready improvements
  - Removed test-specific code, development comments, and hardcoded values
  - Cleaner, more maintainable code structure with proper documentation
  - Maintained all functionality while improving code quality
  - Route `/` still points to the new home component (no routing changes needed)
- **Component Architecture Cleanup** ✅
  - Cleaned up component dependencies to rely on ICUI framework instead of legacy components
  - Maintained only essential UI components and the new ICUI-based home component
  - Prepared codebase for full ICUI framework migration

### December 2024 - ICUI Enhanced Editor & Theme System
- **New ICUIEnhancedEditorPanel.tsx - Combined Implementation** ✅
- **CodeEditor Background & Divider Improvements** ✅
- **Critical Bug Fix - Panel Management** ✅
- **Theme System Refinements** ✅
- **ICUI Enhanced Feedback Implementation** ✅
- **Layout System - Panel Footer Attachment Fix** ✅


