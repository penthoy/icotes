# UI Rewrite Plan - Modular Panel System

## Overview
This document outlines the step-by-step plan for rewriting the UI with a modular, flexible panel system inspired by Blender's UI design principles. The new system will allow users to create, remove, and transform panels dynamically while maintaining complete flexibility.

## Design Principles
1. **Modular Components**: Every UI element is a reusable component
2. **Dynamic Panel System**: Panels can be created, removed, and transformed into any other panel type
3. **Flexible Layout**: Responsive frame that can detect and handle both horizontal and vertical borders
4. **Blender-Inspired**: Complete user control over panel arrangement and types
5. **Inheritance-Based**: Generic panel base class with specialized implementations

## Implementation Steps

### Phase 1: Responsive Frame Foundation
**Goal**: Create the outer frame that handles responsive layout and border detection

#### Step 1.1: Frame Container Component
- Create `src/components/ui/FrameContainer.tsx`
- Implement responsive grid system
- Add border detection for both horizontal and vertical splits
- Support dynamic resizing with drag handles
- Include minimum/maximum size constraints

#### Step 1.2: Split Panel System
- Create `src/components/ui/SplitPanel.tsx`
- Implement horizontal and vertical split functionality
- Add resize handles with visual feedback
- Support nested splits for complex layouts
- Include collapse/expand functionality

#### Step 1.3: Layout State Management
- Create `src/lib/layoutState.ts`
- Implement layout persistence (localStorage)
- Add layout presets (default, code-focused, terminal-focused)
- Support layout import/export

### Phase 2: Generic Panel Base Class
**Goal**: Design a base panel that can be inherited by any specific panel type

#### Step 2.1: Base Panel Component
- Create `src/components/ui/BasePanel.tsx`
- Define common panel properties:
  - `id`: Unique identifier
  - `type`: Panel type (terminal, editor, explorer, etc.)
  - `title`: Display title
  - `closable`: Whether panel can be closed
  - `resizable`: Whether panel can be resized
  - `minimizable`: Whether panel can be minimized
  - `maximizable`: Whether panel can be maximized

#### Step 2.2: Panel Header System
- Create `src/components/ui/PanelHeader.tsx`
- Add title display with edit functionality
- Include panel type selector dropdown
- Add close/minimize/maximize buttons
- Support drag-and-drop for panel rearrangement

#### Step 2.3: Panel Content Container
- Create `src/components/ui/PanelContent.tsx`
- Provide consistent padding and styling
- Support different content types (scrollable, fixed, etc.)
- Include error boundaries for panel content

### Phase 3: Panel Docking and Tabbing System
**Goal**: Create the foundation for IDE-style docked panels with tabbed interfaces

#### Step 3.1: Panel Area Container
- Create `src/components/ui/PanelArea.tsx`
- Implement dockable panel container that holds multiple panels
- Add tabbed interface for multiple panels in same area
- Support drag-and-drop between different panel areas
- Include empty state for drop zones
- Handle tab activation, closing, and reordering

#### Step 3.2: Panel Dock Manager
- Create `src/lib/panelDockManager.ts`
- Manage panel assignment to different dock areas
- Handle panel movement between areas via drag-and-drop
- Implement panel-to-area mapping and persistence
- Support dock area creation and removal
- Track active panels per area

#### Step 3.3: Enhanced Panel Dragging
- Enhance existing drag system to support area docking
- Add visual feedback for valid drop zones
- Implement tab dragging for reordering within areas
- Support dragging panels out to create new floating instances
- Add magnetic docking when dragging near panel areas
- Include preview overlays during drag operations

#### Step 3.4: Integration with Split Panel System
- Modify split panels to host PanelArea components
- Enable panels to be docked into split frame sections
- Support dynamic creation of new split areas via drag
- Maintain layout state when moving panels between areas
- Ensure split resizing works with docked panel content

### Phase 4: Specialized Panel Implementations
**Goal**: Create specific panel types that work within the docking system

#### Step 4.1: Terminal Panel
- Create `src/components/panels/TerminalPanel.tsx`
- Extend BasePanel with terminal-specific features
- Integrate existing Terminal.tsx component
- Add terminal-specific context menu options
- Support multiple terminal instances in tabs

#### Step 4.2: Editor Panel
- Create `src/components/panels/EditorPanel.tsx`
- Extend BasePanel with editor-specific features
- Integrate existing CodeEditor.tsx component
- Add editor-specific toolbar and options
- Support multiple file tabs within single editor panel
- Enable file drag-and-drop between editor areas

#### Step 4.3: Explorer Panel
- Create `src/components/panels/ExplorerPanel.tsx`
- Extend BasePanel with file explorer features
- Integrate existing FileExplorer.tsx component
- Add file tree navigation
- Support file operations (create, delete, rename)

#### Step 4.4: Create ICUITest4.5 Test Page
- Create `tests/integration/icui/ICUITest4.5.tsx`
- Demonstrate the refactored minimal panel implementations
- Test chat panel integration
- Validate that all panels follow the same minimal pattern as ICUITerminalPanel

#### Step 4.5: Refactor EditorPanel and ExplorerPanel to Minimal Implementation
- Refactor `src/icui/components/panels/ICUIEditorPanel.tsx` to be minimal like ICUITerminalPanel
- Refactor `src/icui/components/panels/ICUIExplorerPanel.tsx` to be minimal like ICUITerminalPanel
- Both should be minimal implementations that can be inherited by more complete implementations
- Focus on core functionality only, remove complex features for the base implementation
- Ensure consistent architecture across all panel types

#### Step 4.6: Create ChatPanel Similar to ICUITerminalPanel
- Create `src/icui/components/panels/ICUIChatPanel.tsx`
- Follow the same minimal implementation pattern as ICUITerminalPanel
- Provide AI/LLM/Agent interface capabilities
- Include basic chat interface with message history
- Support for sending/receiving messages
- Maintain consistent styling and behavior with other panels

#### Step 4.7: Create Reference Layout Implementations
- Create layout configurations including:
  - Top/bottom (editor/terminal) split
  - Left (explorer), middle (editor), right (chat) layout
  - "H" layout with split top/bottom in the middle section
- Similar to ICUITEST4 page structure but with these specific layouts
- Create preset configurations for each layout type
- Demonstrate panel docking and area management

#### Step 4.8: Create Reference Implementation for Main Page
- Create new implementation that includes all functionality from current home page
- Use ICUI framework similar to ICUITEST4 page structure
- Integrate with the reference layout implementations from 4.7
- Use this as the foundation for further ICUI development
- Maintain all existing functionality while using the new panel system

#### Step 4.9: Create From-Scratch Editor Implementation
**Problem**: The existing `ICUIEnhancedEditorPanelOld.tsx` imports from `CodeEditor.tsx` and has longstanding issues that couldn't be resolved due to complex CodeMirror configurations and theme conflicts.

**Solution**: Create a completely from-scratch editor implementation that:
- **No Dependencies on CodeEditor.tsx**: Build editor functionality directly without importing existing CodeEditor component
- **Simplified CodeMirror Integration**: Use minimal CodeMirror setup with only essential extensions
- **ICUI Theme Native**: Design theme system to work natively with ICUI CSS variables from the start
- **Minimal but Functional**: Focus on core editor functionality without complex features
- **Clean Architecture**: Follow the same minimal pattern as ICUITerminalPanel

**Implementation Details**:
- Create `src/icui/components/panels/ICUIEditorPanelFromScratch.tsx`
- Use direct CodeMirror 6 setup with minimal extensions:
  - Basic editing (EditorView, EditorState)
  - Syntax highlighting for Python
  - Line numbers and basic editing features
  - Theme integration using ICUI CSS variables
- Maintain consistent styling with other ICUI panels

**Key Differences from Old Implementation**:
- No import of `CodeEditor.tsx` component
- Direct CodeMirror configuration optimized for ICUI
- Simplified theme handling using only ICUI variables
- Streamlined state management
- Minimal external dependencies

**Extra details**:
- Create a ICUITEST4.9 for test

#### Step 4.10: Enhanced Clipboard System with Browser Security Bypass
**Problem**: Browser security restrictions prevent clipboard access in insecure contexts (HTTP, IP addresses), causing clipboard functionality to fail in development and deployment scenarios.

**Solution**: Implement code-server's proven multi-layer clipboard strategy:
- **Layer 1: Native Clipboard API** - Use browser's native clipboard when available (HTTPS, localhost)
- **Layer 2: Server-Side Clipboard Bridge** - Fallback to backend clipboard service via HTTP endpoints
- **Layer 3: CLI Integration** - Support `--stdin-to-clipboard` for terminal applications
- **Layer 4: File Download/Upload** - Ultimate fallback using File API for content transfer

**Implementation Details**:
- Create `src/icui/services/ClipboardService.tsx` with multi-layer clipboard management
- Implement secure context detection and capability testing
- Add progressive fallback hierarchy with user feedback
- Create `src/icui/components/ClipboardManager.tsx` for UI integration
- Update all panel implementations to use enhanced clipboard service
- Add user notifications for clipboard limitations and alternatives

**Key Features**:
- **Context Detection**: Automatically detect secure/insecure context capabilities
- **Progressive Enhancement**: Try best option first, fall back gracefully
- **User Communication**: Clear messaging about limitations and alternatives
- **PWA Support**: Leverage PWA installation to bypass some restrictions
- **Cross-Platform**: Work consistently across all environments

**Files to Create**:
- `src/icui/services/ClipboardService.tsx` - Multi-layer clipboard management
- `src/icui/components/ClipboardManager.tsx` - UI integration component
- `src/icui/hooks/useClipboard.tsx` - React hook for clipboard operations
- Update existing panels (Terminal, Editor, Chat) to use new clipboard system

**Integration Points**:
- Backend clipboard service (`/clipboard` endpoints)
- Browser native clipboard API (when available)
- File download/upload as ultimate fallback
- PWA installation prompts for enhanced capabilities

**Extra details**:
- Create ICUITEST4.10 for testing all clipboard scenarios
- Test across different security contexts (HTTP, HTTPS, localhost, IP addresses)
- Validate fallback behavior and user experience





- Validate fallback behavior and user experience

### Phase 5: Reusable Abstractions from SimpleEditor Analysis
**Goal**: Extract and generalize reusable abstractions identified in the analysis of `simpleeditor.tsx` for broader ICUI framework use.

#### Step 5.1: Notification Service Framework Integration
**Problem**: Frontend components need a unified notification system for user feedback, error handling, and status updates. Currently, `simpleeditor.tsx` implements a custom NotificationService that could be generalized for the entire ICUI framework.

**Solution**: Extract and generalize the notification service from `simpleeditor.tsx` into the ICUI framework core.

**Implementation Details**:
- Create `src/icui/services/ICUINotificationService.tsx` based on patterns from `simpleeditor.tsx`
- Support multiple notification types: success, error, warning, info
- Include toast-style notifications with auto-dismiss
- Provide notification queue management for multiple simultaneous notifications
- Integrate with ICUI theming system using CSS variables
- Support customizable notification positioning and duration
- Export hook `useICUINotifications()` for React components

**Key Features from SimpleEditor Analysis**:
- Type-safe notification methods: `show(message, type, duration?)`
- Automatic cleanup and dismissal
- Visual feedback with appropriate colors for each type
- Non-blocking UI notifications that don't interrupt workflow

#### Step 5.2: Backend Client Abstraction Framework
**Problem**: Multiple components need to interact with backend services, but each implements its own client logic. The `EditorBackendClient` in `simpleeditor.tsx` demonstrates a clean abstraction pattern that should be generalized.

**Solution**: Create a generalized backend client abstraction framework for the ICUI system.

**Implementation Details**:
- Create `src/icui/services/ICUIBackendClient.tsx` as base class
- Extract common patterns from `EditorBackendClient` in `simpleeditor.tsx`:
  - Connection status management and health checks
  - Fallback mode handling when services are unavailable
  - Service availability detection (ICPY, REST API endpoints)
  - Automatic retry logic and error handling
  - Base URL configuration and environment handling

**Key Abstractions from SimpleEditor Analysis**:
- **Connection Management**: `getConnectionStatus()`, `checkServiceAvailability()`
- **Fallback Patterns**: Graceful degradation when backend services are unavailable
- **Error Handling**: Consistent error responses across all backend operations
- **Service Detection**: Dynamic detection of available backend capabilities
- **Environment Adaptation**: Automatic adaptation to different deployment scenarios

**Specialized Clients**:
- Create `ICUIFileClient extends ICUIBackendClient` for file operations
- Create `ICUITerminalClient extends ICUIBackendClient` for terminal operations
- Create `ICUIExecutionClient extends ICUIBackendClient` for code execution

#### Step 5.3: File Management Service Framework
**Problem**: File operations are scattered across different components. The `simpleeditor.tsx` implements comprehensive file CRUD operations with fallback logic that should be standardized.

**Solution**: Extract file management patterns into a reusable ICUI service.

**Implementation Details**:
- Create `src/icui/services/ICUIFileService.tsx`
- Extract patterns from `simpleeditor.tsx` file operations:
  - CRUD operations: `listFiles()`, `getFile()`, `saveFile()`, `createFile()`, `deleteFile()`
  - Language detection from file extensions
  - Workspace path management
  - Auto-save functionality with debouncing
  - File modification tracking

**Key Features from SimpleEditor Analysis**:
- **Language Detection**: Automatic language detection from file extensions
- **Path Management**: Consistent handling of file paths and workspace directories
- **Fallback Content**: Demo/sample files when backend is unavailable
- **Auto-save**: Debounced auto-save with configurable delay
- **Modification Tracking**: Track file changes for UI indicators

#### Step 5.4: Theme Detection and Management Service
**Problem**: Multiple components implement their own theme detection logic. The pattern in both `simpleeditor.tsx` and `ICUIEnhancedEditorPanel.tsx` should be centralized.

**Solution**: Create a unified theme management service for the ICUI framework.

**Implementation Details**:
- Create `src/icui/services/ICUIThemeService.tsx`
- Extract theme detection logic from both editor implementations
- Provide React hook `useICUITheme()` for components
- Support theme switching and persistence
- Integrate with existing ICUI CSS variable system

**Key Features from Editor Analysis**:
- **Automatic Detection**: MutationObserver-based theme class detection
- **Theme Persistence**: Remember user theme preferences
- **CSS Variable Integration**: Work seamlessly with ICUI theming system
- **React Hook Pattern**: Easy integration with React components

### Phase 6: Modular Menu System
**Goal**: Create flexible file and layout menus using the same modular principles

#### Step 6.1: Top Menu Bar
- Create `src/components/ui/MenuBar.tsx`
- Implement dropdown menus for File, Edit, View, Layout
- Add keyboard shortcut support
- Support menu customization

#### Step 6.2: File Menu Implementation
- Create `src/components/menus/FileMenu.tsx`
- Add file operations (New, Open, Save, Close)
- Include recent files list
- Support project management

#### Step 6.3: Layout Menu Implementation
- Create `src/components/menus/LayoutMenu.tsx`
- Add layout presets and templates
- Include panel creation options
- Support layout reset functionality

### Phase 7: Panel Registry and Factory
**Goal**: Create a system to register and instantiate different panel types

#### Step 7.1: Context Menu Component
- Create `src/icui/components/ui/ContextMenu.tsx`
- Support dynamic menu items based on context
- Add panel transformation options
- Include split/merge operations

#### Step 7.2: Panel Registry
- Create `src/icui/lib/panelRegistry.ts`
- Register all available panel types
- Support dynamic panel type loading
- Include panel metadata (icons, descriptions)

#### Step 7.3: Panel Factory
- Create `src/icui/lib/panelFactory.ts`
- Handle panel instantiation based on type
- Support panel configuration and props
- Include error handling for unknown panel types

### Phase 8: Context Menu System
**Goal**: Implement right-click context menus for panel operations

#### Step 8.1: Panel Context Actions
- Create `src/icui/lib/panelActions.ts`
- Implement split panel horizontally/vertically
- Add change panel type functionality
- Support panel duplication and removal

## File Structure

The following file structure will be created as we implement the modular panel system:

```
src/
├── icui/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── FrameContainer.tsx         # Phase 1.1
│   │   │   ├── SplitPanel.tsx             # Phase 1.2
│   │   │   ├── BasePanel.tsx              # Phase 2.1
│   │   │   ├── PanelHeader.tsx            # Phase 2.2
│   │   │   ├── PanelContent.tsx           # Phase 2.3
│   │   │   ├── PanelArea.tsx              # Phase 3.1
│   │   │   ├── MenuBar.tsx                # Phase 6.1
│   │   │   └── ContextMenu.tsx            # Phase 8.1
│   │   ├── panels/
│   │   │   ├── ICUITerminalPanel.tsx      # Phase 4.1
│   │   │   ├── ICUIEditorPanel.tsx        # Phase 4.2
│   │   │   ├── ICUIExplorerPanel.tsx      # Phase 4.3
│   │   │   ├── ICUIChatPanel.tsx          # Phase 4.6
│   │   │   └── ICUIEditorPanelFromScratch.tsx # Phase 4.9
│   │   ├── menus/
│   │   │   ├── FileMenu.tsx               # Phase 6.2
│   │   │   └── LayoutMenu.tsx             # Phase 6.3
│   │   └── ClipboardManager.tsx           # Phase 4.10
│   ├── services/
│   │   ├── ICUINotificationService.tsx    # Phase 5.1
│   │   ├── ICUIBackendClient.tsx          # Phase 5.2
│   │   ├── ICUIFileService.tsx            # Phase 5.3
│   │   ├── ICUIThemeService.tsx           # Phase 5.4
│   │   └── ClipboardService.tsx           # Phase 4.10
│   ├── hooks/
│   │   ├── useICUINotifications.tsx       # Phase 5.1
│   │   ├── useICUITheme.tsx               # Phase 5.4
│   │   └── useClipboard.tsx               # Phase 4.10
│   └── lib/
│       ├── layoutState.ts                 # Phase 1.3
│       ├── panelDockManager.ts            # Phase 3.2
│       ├── panelRegistry.ts               # Phase 7.1
│       ├── panelFactory.ts                # Phase 7.2
│       └── panelActions.ts                # Phase 8.2
├── components/
│   └── ui/                                # Legacy components (to be migrated)
└── tests/
    └── integration/
        └── icui/
            ├── ICUITest4.5.tsx            # Phase 4.4
            ├── ICUITest4.9.tsx            # Phase 4.9
            └── ICUITest4.10.tsx           # Phase 4.10
```

## Current Status

- ✅ **Phase 1-3**: Framework foundation and panel system
- ✅ **Phase 4**: Specialized panel implementations (in progress)
- 🔄 **Phase 5**: Reusable abstractions from SimpleEditor analysis (next priority)
- ⏳ **Phase 6-9**: Advanced features and menu systems

## Next Steps

1. Complete Phase 4 remaining steps (4.10 clipboard system)
2. Begin Phase 5 implementation of reusable abstractions
3. Extract NotificationService from simpleeditor.tsx
4. Create ICUIBackendClient base class
5. Implement unified theme management service
