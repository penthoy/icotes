## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create a powerful, The world's most powerful notebook for developers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal(similar to replit), 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework.

### In Progress

## Current Status: Integration Phase Complete ✅

### ✅ Completed Tasks
- ✅ Copied `home.tsx` to `tests/integration/inthome.tsx` for integration testing
- ✅ Refactored `inthome.tsx` to use only existing components and local state
- ✅ Removed out-of-scope `BackendConnectedEditor` component  
- ✅ Added `inthome.tsx` to `App.tsx` with `/inthome` route for direct testing
- ✅ Verified build passes with no errors
- ✅ Exposed `WORKSPACE_ROOT` in `.env` as `VITE_WORKSPACE_ROOT` for frontend use
- ✅ **Updated BackendConnectedTerminal.tsx to follow simpleterminal.tsx pattern** 
  - Complete refactor using direct WebSocket connection
  - Removed complex backend state management
  - Added clipboard functionality
  - Applied proper theming and scrolling
  - Verified build passes with no errors
  - Fixed double WebSocket connection issue by separating terminal initialization from theme updates
- ✅ **Use WORKSPACE_ROOT from .env to sync root of all panels**
  - Added workspace root reading from `VITE_WORKSPACE_ROOT` 
  - Added workspace root indicator to UI status display
  - Integrated workspace root into `inthome.tsx` component
  - Verified build passes with no errors
- ✅ **Updated BackendConnectedExplorer.tsx to use VITE_WORKSPACE_ROOT**
  - Updated initial directory loading to use workspace root
  - Modified file and folder creation to work relative to workspace root
  - Added workspace root indicator to explorer header
  - Fixed double API path issues (/api/api/files) with direct backend integration
  - Verified build passes with no errors
- ✅ **Updated BackendConnectedEditor.tsx with direct backend integration**
  - Complete rewrite following simpleeditor.tsx pattern with direct API calls
  - Removed complex backend state management (useBackendState/useBackendContext)
  - Added CodeMirror 6 integration with syntax highlighting and theming
  - Implemented multi-file tabs with backend synchronization
  - Added auto-save with debouncing for file operations
  - Integrated workspace root support (VITE_WORKSPACE_ROOT)
  - Added connection status display and error handling
  - Updated inthome.tsx to use new BackendConnectedEditor
  - **Fixed workspace file loading** - now loads actual files from workspace instead of demo files
  - **Fixed demo mode issue in inthome.tsx** - removed hardcoded demo files to let BackendConnectedEditor handle file loading
  - **Fixed tab flashing bug** - removed duplicate file state management causing conflicts
  - **Fixed CodeMirror cursor positioning issue** - followed exact ICUIEnhancedEditorPanel pattern:
    * Removed activeFile?.id from editor initialization dependencies (was causing unnecessary recreation)  
    * Added content comparison in updateListener to prevent unnecessary updates
    * Fixed content update effect to use currentContent.length instead of state.doc.length
    * Cleaned up unused duplicate getLanguageFromExtension function
  - Verified build passes with no errors

### In Progress

## Future task


- [] Update integration details: explorer is empty by defaul, but populates 

- [] work on integration_plan.md 2.3: Editor Integration
- [] work on icpy_plan.md 
- [] work on icui_plan.md 4.10 clipboard, need to update 5 and beyond

- [] housekeeping, clean up unused routes in App.tsx
  
- [] work on integration_plan.md 2.3: Editor Integration
- [] work on icpy_plan.md 
- [] work on icui_plan.md 4.10 clipboard, need to update 5 and beyond

-- Milestone 1:
Complete icui-icpy connection and integration plan so that the old home route is using icpy backend.

-- Milestone 2:
home route refined and first mvp complete, can be showned.
critical features:
you can start using your own APIs to create simple software.

-- Milestone 3:
Agent integration:
Agents can edit files.
features: history, context

-- Milestone 4:
Advanced agents
Everything that copilot, cursor can do

-- Milestone 5:
uncharted teritories, vanture where no other editor has gone, features:
multiple agents working side by side in async. they're AI employees, in crew AI they'll be given name and backstory and role, this is for the purpose of devide and concour, they'll each have limited context so in their context they'll be specialized in one part of the code base, such as back end, frontend or integration, they're able to talk to each other


-- Bug Fix:
- [] Fix panel flickering issue
- [] Creating a new Terminal panel in the same area for example in the bottom, it'll look exactly the same as the other terminal, it seems like it is just displaying exactly what's in that terminal, this is the wrong behavior, if I create a new terminal panel at the top, it looks correct, please fix this, creating a new Terminal panel with the arrow drop down, regardless of where it was created, should be an independent terminal. this does for all other panels. not just the terminal.

- [] when dragged out from one panel area to another, it should show the panel that's left, instead of the dragable area.

-- api backend
- [] create an api layer between the front end and backend.
- [] This api layer can also be used in the comand line which also have hooks to the UI to do things like open a file in editor or have AI assistant use tools to edit file etc.
- api feature: detect what view is active so that the AI can have the correct context when you talk to it, it saves the state of the
- we'll add these endpoints later, but first we need to create a design document named api_design.md in docs folder and wait for me to review/edit it before proceed with building this layer.

-- Features:
Add a settings menu under File menu
Add a custom sub menu under Layout, inside custom, there should be a save layout button, when clicked, it should give a popup to name your layout and click ok, once clicked it'll save the state of the current layout. as a new custom layout.
-- Later
A Panel installer,
maya style code executor.

## Recently Finished

- [✅] **Fixed BackendConnectedEditor Cursor Positioning Bug** - **COMPLETED** - Successfully debugged and fixed the critical cursor positioning issue in `inthome.tsx` BackendConnectedEditor where typing caused the cursor to jump to the beginning instead of staying at the current position. Root cause was stale closure issues in the CodeMirror updateListener and unnecessary editor recreations. Applied fixes following the working ICUIEnhancedEditorPanel pattern:
  * **Fixed editor recreation logic** - Removed `activeFile?.id` from dependencies, only recreate editor when theme or language changes (not file switches)
  * **Fixed updateListener closure issue** - Replaced stale `activeFile.content` comparison with `currentContentRef.current` to avoid stale closure problems
  * **Added content reference tracking** - Introduced `currentContentRef` to properly track current editor content and prevent update loops
  * **Fixed content update effect** - Removed `activeFile?.id` dependency that was causing unnecessary content dispatches
  * **Synchronized content updates** - Ensured `currentContentRef` is updated whenever editor content changes to maintain consistency
  * Verified build passes with no errors
  * Editor now maintains proper cursor position during typing and file switches
  * Multi-file editing experience is now seamless and responsive

- [✅] **Integration Plan Phase 2.4 - Home.tsx Rewrite and ICPY Preparation** - **COMPLETED** - Successfully completed rewrite of home.tsx for ICPY integration as specified in integration_plan.md 2.4. Copied original home.tsx to tests/integration/inthome.tsx and refactored it for backend integration readiness. Cleaned up component by removing non-existent BackendConnectedEditor references, simplified backend state management with graceful fallbacks, replaced complex backend hooks with simple local state management (ready for future backend integration), maintained existing BackendConnectedExplorer and BackendConnectedTerminal integration, and added proper error handling and connection status display. Component now uses ICUIEnhancedEditorPanel directly for editor functionality while keeping the structure ready for future ICPY backend connection. The integrated home component is prepared with proper theme management, layout controls, and panel management system ready for full backend synchronization.

- [✅] **Integration Plan Phase 2.4: Comprehensive Integration Test Environment** - **COMPLETED** - Implemented comprehensive three-panel integration test environment as specified in integration_plan.md Step 2.4. Created BackendConnectedEditor component (`tests/integration/components/BackendConnectedEditor.tsx`) that wraps SimpleEditor with enhanced integration capabilities. Built ComprehensiveIntegrationTest component (`tests/integration/components/ComprehensiveIntegrationTest.tsx`) providing unified IDE-like interface with Explorer (left 25%), Editor (center 50%), and Terminal (right 25%) panels. Added IntegrationTestControls component (`tests/integration/components/IntegrationTestControls.tsx`) with comprehensive test automation including file creation, directory operations, terminal management, code execution, and cross-panel workflow validation. Updated integration route (`tests/integration/integration.tsx`) to support both basic and comprehensive test modes. All components integrate seamlessly with existing BackendConnectedExplorer, SimpleEditor, and BackendConnectedTerminal components while maintaining full ICPY backend connectivity. Accessible at `/integration` with comprehensive mode providing complete IDE experience demonstrating file-to-editor-to-terminal workflow integration.

- [✅] **Event Broadcasting System Implementation** - **COMPLETED** - Implemented advanced Event Broadcasting System (`backend/icpy/core/event_broadcaster.py`) as specified in icpy_plan.md Step 4.2. Features include priority-based event broadcasting (low, normal, high, critical), targeted delivery modes (broadcast, multicast, unicast), advanced event filtering with permissions and client type support, client interest management with topic patterns, comprehensive event history and replay functionality, and seamless integration with MessageBroker and ConnectionManager. Added full test suite (`backend/tests/icpy/test_event_broadcaster.py`) with 26 passing tests covering all functionality including service lifecycle, broadcasting, filtering, history, replay, error handling, statistics, and performance. Service provides global instance management and supports real-time event-driven communication across WebSocket, HTTP, and CLI clients.

- [✅] **ICUI Layout Menu Implementation** - **COMPLETED** - Created comprehensive LayoutMenu component (`src/icui/components/menus/LayoutMenu.tsx`) as specified in icui_plan.md 6.3. Features include layout templates and presets (Default, Code Focused, Terminal Focused), custom layout management (save, load, delete with localStorage integration), panel creation options for all panel types (editor, terminal, explorer, output, browser, preview), layout reset functionality, layout import/export capabilities, and full ICUILayoutStateManager integration. Added supporting CSS styles (`src/icui/styles/LayoutMenu.css`) with dark theme support, responsive design, and accessibility features. Includes comprehensive test page (`/icui-layout-menu-test`) demonstrating all functionality with interactive layout state management, panel creation/removal, and layout history tracking.

- [✅] **State Synchronization Service Implementation** - **COMPLETED** - Implemented comprehensive State Synchronization Service (`backend/icpy/services/state_sync_service.py`) as specified in icpy_plan.md Phase 4.1. Features include multi-client state mapping and synchronization, state diffing and incremental updates, conflict resolution (last-writer-wins, first-writer-wins, merge strategies), client presence awareness with cursor tracking and file viewing, state checkpoints and rollback functionality, event-driven communication via message broker, and comprehensive error handling. Added full integration test suite (`backend/tests/icpy/test_state_sync_service.py`) with 23 passing tests covering all functionality including service lifecycle, client registration/unregistration, state changes, conflict resolution, presence management, checkpoints, and concurrent operations. Service integrates seamlessly with existing message broker and connection manager architecture.

- [✅] **State Synchronization Service Implementation** - **COMPLETED** - Implemented comprehensive State Synchronization Service (`backend/icpy/services/state_sync_service.py`) as specified in icpy_plan.md Phase 4.1. Features include multi-client state mapping and synchronization, state diffing and incremental updates, conflict resolution (last-writer-wins, first-writer-wins, merge strategies), client presence awareness with cursor tracking and file viewing, state checkpoints and rollback functionality, event-driven communication via message broker, and comprehensive error handling. Added full integration test suite (`backend/tests/icpy/test_state_sync_service.py`) with 23 passing tests covering all functionality including service lifecycle, client registration/unregistration, state changes, conflict resolution, presence management, checkpoints, and concurrent operations. Service integrates seamlessly with existing message broker and connection manager architecture.

- [✅] **ICUI File Menu Implementation** - **COMPLETED** - Created comprehensive FileMenu component (`src/icui/components/menus/FileMenu.tsx`) as specified in icui_plan.md 6.2. Features include file operations (New, Open, Save, Save As, Close), recent files tracking with localStorage persistence, project management (Open/Close Project), settings access, keyboard shortcuts support, and full FileService integration. Added supporting CSS styles (`src/icui/styles/FileMenu.css`) with dark theme support, and comprehensive test page (`/icui-file-menu-test`) demonstrating all functionality. The component follows ICUI design principles with proper error handling, loading states, and fallback mode support.

- [✅] **Critical Backend Issues Resolution** - **COMPLETED** - Fixed all critical backend issues in icpy_plan.md Phase 0: Critical Infrastructure Fixes. Resolved Pydantic version compatibility (v2.5.0 in virtual environment vs v1.10.14 in system), ensured ICPY modules load successfully when using virtual environment, removed temporary fallback code (lines 521-647) from backend/main.py, and restored proper ICPY REST API integration. Backend now shows "icpy modules loaded successfully" and all services initialize correctly with event-driven architecture active.
## Recently Finished
- [✓] work on icui_plan.md Phase 6.1: **Top Menu Bar Implementation** - Created `src/icui/components/ui/MenuBar.tsx` with complete dropdown menu system including File, Edit, View, and Layout menus. Features keyboard shortcut support (Ctrl+N, Ctrl+S, etc.), menu customization, submenu support, ICUI theming integration, and notification system integration. Includes test page at `/icui-test6.1` route demonstrating all functionality including custom menus, keyboard shortcuts, and accessibility features.

- [✓] work on icui_plan.md 5.3: **File Management Service Framework** - Created `src/icui/services/fileService.tsx` with comprehensive file CRUD operations, language detection from extensions, auto-save with debouncing, file modification tracking, workspace path management, and fallback mode support. Includes both ICPY backend integration and client-side fallback capabilities.

- [✓] work on icui_plan.md 5.4: **Theme Detection and Management Service** - Created `src/icui/services/themeService.tsx` with MutationObserver-based automatic theme detection, React hook `useTheme()` integration, theme persistence and switching, multiple theme support (GitHub, Monokai, One Dark, Solarized), and ICUI CSS variable integration.

- [✓] **Service Naming Cleanup** - Removed redundant ICUI prefixes from service files since they're already in the `icui/` folder. Updated all imports and references: `notificationService.tsx`, `backendClient.tsx`, `FileClient`, `TerminalClient`, `ExecutionClient`, `useNotifications()` hook.

-- Framework Enhancement:
- [✓] **Notification Service Integration** - Extract and generalize the NotificationService from `tests/integration/simpleeditor.tsx` into `src/icui/services/notificationService.tsx`. The current implementation in simpleeditor provides a clean pattern for toast notifications with auto-dismiss, multiple types (success, error, warning), and non-blocking UI feedback.

- [✓] **Backend Client Abstraction** - Create `src/icui/services/backendClient.tsx` base class based on the `EditorBackendClient` pattern from simpleeditor. Key features include connection status management, fallback mode handling, service availability detection, and consistent error handling across all backend operations.

- [] **File Management Service** - Extract file CRUD operations from simpleeditor into `src/icui/services/fileService.tsx`. Include language detection, workspace path management, auto-save with debouncing, and file modification tracking. The current implementation handles both ICPY and fallback modes effectively.

- [] **Theme Management Service** - Centralize theme detection logic from multiple editor components into `src/icui/services/themeService.tsx` with `useTheme()` hook. Both simpleeditor and ICUIEnhancedEditorPanel implement similar MutationObserver-based theme detection that should be unified.

- [] **Connection Status Components** - Create reusable connection status indicators based on the pattern in simpleeditor. Include visual connection state, error reporting, and refresh functionality for backend health monitoring.

- [] **Auto-save Framework** - Generalize the debounced auto-save pattern from simpleeditor into a reusable hook or service. Include configurable delays, modification tracking, and integration with notification system for save confirmations.



