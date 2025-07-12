# JavaScript Code Editor - Project Roadmap

## Project Overview
A web-based JavaScript code editor built with React, CodeMirror 6, and modern web technologies. The goal is to create a powerful, user-friendly code editor with real-time execution capabilities.

## In Progress


## Future task
-- Fix UI issues
- [] Fix Terminal speed issue
- [] Fix panel flickering issue.
- [] Terminal should auto go to botthom after typed something and pressed enter
- [] Active Panel tabs should high lighter in color while inactive tabs are darker just like Editor Panel tabs
- [] dragable panel tabs, should allow reordering
- [] dragable editor tabs
- [] terminal history is black.

-- api backend
- [] create an api layer between the front end and backend.
- [] This api layer can also be used in the comand line which also have hooks to the UI to do things like open a file in editor or have AI assistant use tools to edit file etc.
- api feature: detect what view is active so that the AI can have the correct context when you talk to it, it saves the state of the
- we'll add these endpoints later, but first we need to create a design document named api_design.md in docs folder and wait for me to review/edit it before proceed with building this layer.

-- Later
A Panel installer,
maya style code executor.

## Recently Finished

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


