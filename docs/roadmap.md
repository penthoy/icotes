# JavaScript Code Editor - Project Roadmap

## Project Overview
A web-based JavaScript code editor built with React, CodeMirror 6, and modern web technologies. The goal is to create a powerful, user-friendly code editor with real-time execution capabilities.

## In Progress 🚧
- [🚧] **ICUI Framework Phase 3 - Panel Docking and Tabbing System**
  - **CRITICAL FOUNDATION FOR IDE FUNCTIONALITY**
  - Implementing docked panel areas with tabbed interfaces
  - Enabling drag-and-drop between panel areas
  - Building the foundation for VS Code-like editor experience
  - Step 3.1: Panel Area Container (✅ Implemented)
  - Step 3.2: Panel Dock Manager (🚧 Basic implementation)  
  - Step 3.3: Enhanced Panel Dragging (✅ Tab dragging working)
  - Step 3.4: Integration with Split Panels (✅ Working)

- [✅] continue with icui 2.1 from ui_rewrite.md (Base Panel Component), create a icui-test2 route, so that we don't bog down too much on a single test page.
- [✅] create folder that follows indstry standard on test driven development, and put these test files inside. try to follow industry convention as much as possible.

## Future tasks:
- [] Cleanup: remove anything under the following directories so that tempo templates are removed if they are not being used in this repo
- [] Backend: refactor the main.py and create a terminal.py move everything terminal related from main.py to terminal.py so that it is more modular.

- [] Add agent chat tab on the left side same place as the Explorer with a tab, similar to how vs code extensions are installed on the left side.

## Recently Finished 🎉
- [✅] Created comprehensive UI rewrite plan (ui_rewrite.md) for modular panel system inspired by Blender's UI design
  - Detailed 6-phase implementation plan with step-by-step breakdown
  - Modular component architecture design
  - Generic panel base class with specialized implementations
  - Dynamic panel creation/removal and transformation system
  - Responsive frame foundation with border detection
  - File and layout menu system design
  - Panel registry and factory pattern implementation
  - Complete migration strategy and rollback plan
  - Testing strategy and success criteria defined
  - Timeline estimate: 14-21 days for full implementation

- [✅] **ICUI Framework Step 1.1 - Frame Container Component** 
  - Created ICUI framework with dedicated folder structure and ICUI prefixes
  - Implemented responsive frame container with border detection
  - Added dynamic resize handles with visual feedback
  - Created TypeScript type definitions for layout system
  - Built responsive hook for viewport detection and breakpoint management
  - Added CSS styles with accessibility and dark mode support
  - Created test component accessible at `/icui-test` route
  - Added comprehensive documentation and README
  - Successfully builds without errors
  - Framework is modular and reusable for other projects

- [✅] **ICUI Framework Step 1.1 - Critical Bug Fixes**
  - Fixed infinite loop in border detection causing tens of thousands of console messages
  - Implemented proper debouncing for ResizeObserver and viewport changes
  - Added change detection to prevent unnecessary state updates
  - Fixed responsive hook to maintain object references when unchanged
  - Reduced debug logging spam while maintaining useful development information
  - Added proper cleanup for timeout handlers
  - Improved performance by preventing recursive re-renders
  - Console messages now properly controlled and non-spamming

- [✅] **ICUI Framework Step 1.2 - Split Panel System**
  - Implemented horizontal and vertical split functionality with resizable handles
  - Added collapse/expand functionality with intuitive controls
  - Built support for nested splits enabling complex layouts
  - Created comprehensive TypeScript types for split panel system
  - Added CSS styling with smooth transitions and visual feedback
  - Enhanced test component with multiple split panel demonstrations
  - **Performance Optimizations (v1.2.1):**
    - Fixed drag delay by implementing requestAnimationFrame for smooth resizing
    - Reduced minimum panel size from 100px to 2px for unrestricted dragging
    - Added proper animation frame cleanup to prevent memory leaks
    - Optimized state updates to reduce unnecessary re-renders during drag
    - Split panels can now be dragged almost to edges while maintaining grab handle
  - **Rubberband Effect Fix (v1.2.2):**
    - Eliminated rubberband/lag effect during drag operations
    - Implemented conditional CSS transitions (off during drag, on for collapse/expand)
    - Simplified drag handling for instant visual feedback
    - Achieved perfectly smooth and responsive dragging experience
  - Successfully builds and runs without errors
  - All split panel features working robustly with excellent performance

- [✅] **ICUI Framework Step 1.3 - Layout State Management**
  - Created comprehensive layout state management system with TypeScript types
  - Implemented persistent storage using localStorage with auto-save functionality
  - Built layout presets system (Default, Code Focused, Terminal Focused)
  - Added export/import functionality for sharing layouts between users
  - Created undo/redo system with configurable history size
  - Developed React hooks for easy integration (useICUILayoutState, useCurrentLayout, useLayoutPresets)
  - Built interactive Layout Preset Selector component with live preview
  - Added proper error handling and loading states
  - Successfully handles layout persistence across browser sessions
  - **Critical Bug Fixes (v1.3.1):**
    - Fixed "Layout manager not initialized" runtime errors
    - Resolved circular type reference issues between interface and class names
    - Improved hook initialization with proper error handling and fallbacks
    - Enhanced export functionality with robust clipboard handling and fallbacks
    - Fixed TypeScript compilation errors and type mismatches
    - Added proper loading states and error boundaries
  - All features working robustly with excellent user experience

- [✅] **ICUI Framework Step 2.1 - Base Panel Component System (Phase 2)**
  - Created comprehensive panel type system with TypeScript definitions
  - Implemented ICUIBasePanel component with common panel properties (id, type, title, closable, resizable, minimizable, maximizable, draggable)
  - Built ICUIPanelHeader with title editing, type selector dropdown, and control buttons (minimize, maximize, close)
  - Developed ICUIPanelContent with error boundaries, consistent styling, and content type support
  - Added panel management hook (useICUIPanels) for creating, updating, removing, and managing panel instances
  - Implemented panel positioning, z-index management, and active panel tracking
  - Created panel utility functions and factory methods for easy panel creation
  - Added comprehensive CSS styling with responsive design and accessibility features
  - Built ICUITest2 component accessible at `/icui-test2` route for testing panel functionality
  - **Features Include:**
    - 8 panel types: terminal, editor, explorer, output, properties, timeline, inspector, custom
    - Full drag-and-drop support for panel repositioning
    - Resize handles for dynamic panel sizing
    - Panel state management (normal, minimized, maximized, closed)
    - Panel cloning and duplication functionality
    - Type-safe panel configuration and instance management
    - Error boundaries for robust panel content handling
  - Successfully builds and runs without errors
  - Framework version updated to v2.0.0

- [✅] **Test-Driven Development Structure Implementation**
  - Created industry-standard test directory structure: `/tests/unit`, `/tests/integration`, `/tests/e2e`, `/tests/fixtures`
  - Moved ICUI test components to `/tests/integration/icui/` directory
  - Updated import paths and routing to work with new structure
  - Follows Jest and testing best practices for scalable test organization
  - Prepared foundation for comprehensive testing suite

- [✅] **ICUI Framework Phase 3.1 - Panel Docking System Foundation**
  - **CRITICAL MILESTONE: IDE-Style Docking Implementation**
  - Created ICUIPanelArea component for dockable panel containers
  - Implemented tabbed interface for multiple panels in same area
  - Added drag-and-drop support between different panel areas
  - Built empty state UI for drop zones
  - Integrated with existing split panel system for complex layouts
  - Added comprehensive CSS styling for tabs, docking, and panel content
  - Created ICUITest3 component accessible at `/icui-test3` route
  - **Key Features:**
    - Tab-based panel switching within areas
    - Visual drag-and-drop feedback between areas
    - Panel-specific content rendering (editor, terminal, explorer)
    - Responsive tab design with overflow handling
    - Integration with Phase 1.2 split panel system
    - Empty area states with drop zone indicators
  - Successfully builds and runs without errors
  - **This addresses the core request for attached/docked panels instead of floating panels**
  - Framework version updated to v3.0.0 (Phase 3 foundation)

*This section will be moved to Working.md and CHANGELOG.md during housekeeping.*

## Completed Features ✅

### Core Editor Functionality
- ✅ CodeMirror 6 integration with syntax highlighting
- ✅ JavaScript code execution with console output capture
- ✅ Real-time error handling and display
- ✅ Code completion and bracket matching
- ✅ Line numbers and code folding

### User Interface
- ✅ Clean, responsive design with Tailwind CSS
- ✅ Light/dark theme toggle with system preference detection
- ✅ Collapsible output panel for execution results
- ✅ Professional header with branding and controls

### Technical Infrastructure
- ✅ Vite build system with React and TypeScript
- ✅ ShadCN UI component library integration
- ✅ Proper error boundary and handling

### File Management System
- 🚧 VS Code-like tabbed interface for multiple files
- 🚧 File creation, renaming, and deletion
- 🚧 File modification tracking (unsaved changes indicator)
- 🚧 Keyboard shortcuts for file operations

### Enhanced Editor Features
- 🚧 Multiple language support (currently JavaScript only)
- 🚧 Advanced code formatting and linting
- 🚧 Search and replace functionality
- 🚧 Code minimap for navigation

## Planned Features 📋

### Advanced Functionality
- 📋 File tree/explorer sidebar
- 📋 Project workspace management
- 📋 Import/export functionality for code files
- 📋 Code sharing and collaboration features

### Developer Experience
- 📋 Customizable editor settings and preferences
- 📋 Plugin system for extensibility
- 📋 Integrated terminal for command execution
- 📋 Git integration for version control

### Performance & Optimization
- 📋 Large file handling optimization
- 📋 Lazy loading for better performance
- 📋 Offline functionality with service workers
- 📋 Progressive Web App (PWA) capabilities

### Testing & Quality
- 📋 Comprehensive unit and integration tests
- 📋 End-to-end testing with Playwright
- 📋 Performance monitoring and analytics
- 📋 Accessibility improvements (WCAG compliance)

## Technical Debt & Improvements

### Code Quality
- 📋 Refactor component structure for better maintainability
- 📋 Implement proper TypeScript strict mode
- 📋 Add comprehensive error handling throughout the app
- 📋 Optimize bundle size and loading performance

### Documentation
- 📋 API documentation for components
- 📋 User guide and tutorials
- 📋 Contributing guidelines for open source
- 📋 Deployment and hosting documentation

## Current Sprint Focus

### Priority 1: File Management
1. Complete tabbed interface implementation
2. Add file creation and deletion functionality
3. Implement unsaved changes tracking
4. Add keyboard shortcuts (Ctrl+N, Ctrl+S, etc.)

### Priority 2: Enhanced Editor
1. Add search and replace functionality
2. Implement code formatting options
3. Add more language support beyond JavaScript
4. Improve error handling and user feedback

## Architecture Notes

### Key Components
- `Home.tsx`: Main application container and state management
- `CodeEditor.tsx`: CodeMirror 6 wrapper with custom extensions
- `OutputPanel.tsx`: Execution results and error display
- `FileTabs.tsx`: File management and tabbed interface
- `ThemeToggle.tsx`: Theme switching functionality

### State Management
- Currently using React useState for local state
- Consider implementing Context API or Zustand for complex state
- File management state needs centralized handling

### Performance Considerations
- CodeMirror 6 handles large files efficiently
- Output panel should limit displayed logs to prevent memory issues
- Consider virtualization for file lists in future file explorer

---

*Last updated: [Current Date]*
*Version: 1.0.0*
