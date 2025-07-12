# JavaScript Code Editor - Project Roadmap

## Project Overview
A web-based JavaScript code editor built with React, CodeMirror 6, and modern web technologies. The goal is to create a powerful, user-friendly code editor with real-time execution capabilities.

## In Progress

## Future task

-- Fix UI issues
- [] Fix panel flickering issue.
- [] Terminal should auto go to botthom after typed something and pressed enter
- [] Active Panel tabs should high lighter in color while inactive tabs are darker just like Editor Panel tabs
- [] create an api layer between the front end and backend.
- [] This api layer can also be used in the comand line which also have hooks to the UI to do things like open a file in editor or have AI assistant use tools to edit file etc.
- api feature: detect what view is active so that the AI can have the correct context when you talk to it, it saves the state of the
- we'll add these endpoints later, but first we need to create a design document named api_design.md in docs folder and wait for me to review/edit it before proceed with building this layer.

-- Later
A Panel installer,
maya style code executor.

## Recently Finished

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


