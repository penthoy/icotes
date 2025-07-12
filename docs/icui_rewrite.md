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

### Phase 5: Modular Menu System
**Goal**: Create flexible file and layout menus using the same modular principles

#### Step 5.1: Top Menu Bar
- Create `src/components/ui/MenuBar.tsx`
- Implement dropdown menus for File, Edit, View, Layout
- Add keyboard shortcut support
- Support menu customization

#### Step 5.2: File Menu Implementation
- Create `src/components/menus/FileMenu.tsx`
- Add file operations (New, Open, Save, Close)
- Include recent files list
- Support project management

#### Step 5.3: Layout Menu Implementation
- Create `src/components/menus/LayoutMenu.tsx`
- Add layout presets and templates
- Include panel creation options
- Support layout reset functionality

### Phase 6: Panel Registry and Factory
**Goal**: Create a system to register and instantiate different panel types

#### Step 5.1: Panel Registry
- Create `src/lib/panelRegistry.ts`
- Register all available panel types
- Support dynamic panel type loading
- Include panel metadata (icons, descriptions)

#### Step 6.2: Panel Factory
- Create `src/lib/panelFactory.ts`
- Handle panel instantiation based on type
- Support panel configuration and props
- Include error handling for unknown panel types

### Phase 7: Context Menu System
**Goal**: Implement right-click context menus for panel operations

#### Step 6.1: Context Menu Component
- Create `src/components/ui/ContextMenu.tsx`
- Support dynamic menu items based on context
- Add panel transformation options
- Include split/merge operations

#### Step 7.2: Panel Context Actions
- Create `src/lib/panelActions.ts`
- Implement split panel horizontally/vertically
- Add change panel type functionality
- Support panel duplication and removal

## File Structure
```
src/
├── components/
│   ├── ui/
│   │   ├── FrameContainer.tsx
│   │   ├── SplitPanel.tsx
│   │   ├── BasePanel.tsx
│   │   ├── PanelHeader.tsx
│   │   ├── PanelContent.tsx
│   │   ├── PanelArea.tsx          # NEW: Dockable panel container
│   │   ├── MenuBar.tsx
│   │   └── ContextMenu.tsx
│   ├── panels/
│   │   ├── TerminalPanel.tsx
│   │   ├── EditorPanel.tsx
│   │   ├── ExplorerPanel.tsx
│   │   └── OutputPanel.tsx
│   ├── menus/
│   │   ├── FileMenu.tsx
│   │   ├── LayoutMenu.tsx
│   │   └── ViewMenu.tsx
│   └── [existing components remain]
├── lib/
│   ├── layoutState.ts
│   ├── panelDockManager.ts        # NEW: Panel docking management
│   ├── panelRegistry.ts
│   ├── panelFactory.ts
│   └── panelActions.ts
└── types/
    ├── panel.ts
    ├── layout.ts
    └── dock.ts                    # NEW: Docking system types
```

## Migration Strategy
1. **Phase 1-2**: Build foundation without touching existing UI
2. **Phase 3**: Implement docking and tabbing system - **CRITICAL FOR IDE FUNCTIONALITY**
3. **Phase 4**: Create panel wrappers for existing components that work in dock areas
4. **Phase 5**:
6. **Phase 5**: Add menu system and panel registry
5. **Phase 7**: Implement context menus and advanced features
6. **Phase 8**: Create toggle to switch between old and new UI
7. **Phase 9**: Test thoroughly and migrate completely

## Testing Strategy
- Unit tests for each component
- Integration tests for panel interactions
- Visual regression tests for UI consistency
- Performance tests for large numbers of panels
- Accessibility tests for keyboard navigation

## Rollback Plan
- Keep existing UI components intact during development
- Implement feature flag to toggle between old and new UI
- Maintain backward compatibility during transition
- Document migration path for users

## Timeline Estimate
- Phase 1: 2-3 days (Frame foundation)
- Phase 2: 2-3 days (Generic panel system)
- **Phase 3: 4-5 days (Docking and tabbing system) - CRITICAL FOUNDATION**
- Phase 4: 3-4 days (Specialized panels with docking support)
- Phase 5: 2-3 days (Menu system)
- Phase 6: 1-2 days (Registry and factory)
- Phase 7: 2-3 days (Context menus)
- Testing and refinement: 2-3 days

**Total estimated time**: 18-26 days

## Success Criteria
- [ ] Users can create/remove panels dynamically
- [ ] Any panel can be transformed into any other panel type
- [ ] **Panels can be docked into areas with tabbed interfaces**
- [ ] **Multiple panels can share the same area with tab switching**
- [ ] **Panels can be dragged between different dock areas**
- [ ] **Empty areas show drop zones for panel docking**
- [ ] Layout is fully responsive and handles various screen sizes
- [ ] Panel arrangement can be saved and restored
- [ ] Performance remains smooth with multiple panels
- [ ] Accessibility standards are maintained
- [ ] Existing functionality is preserved
- [ ] Migration path is smooth and non-disruptive

---

*This plan is ready for review and modification before implementation begins.*
