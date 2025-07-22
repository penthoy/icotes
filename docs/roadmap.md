## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create a powerful, The world's most powerful notebook for developers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal(similar to replit), 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework.

### Phase 3: Theme & Consistency (✅ COMPLETED) 

**Status: COMPLETED** ✅

### 3.1 Theme Unification (✅ COMPLETED)
**Goal:** Fix theme inconsistencies across all components and routes

- ✅ **ICUI Framework Theming**: All ICUI components now use CSS variables for consistent theming across all themes
- ✅ **Terminal Theme Consistency**: 
  - ICUIEnhancedTerminalPanel: Fully refactored to use ICUI CSS variables
  - BackendConnectedTerminal: Refactored to use ICUI CSS variables for all terminal backgrounds and colors
- ✅ **Tab Theme Consistency**: 
  - ICUI tab system: Updated to use unified CSS variables
  - BackendConnectedEditor custom tabs: Refactored to use ICUI theme variables
- ✅ **Color Variable Unification**: All color variables unified in icui-themes.css
- ✅ **Cross-Route Consistency**: Both home route and /inthome route now have matching themes

**Technical Implementation:**
- All terminal and editor components now use `getComputedStyle(document.documentElement).getPropertyValue('--icui-bg-primary')` for background consistency
- Terminal color schemes use ICUI terminal color variables for all ANSI colors
- Tab systems unified to use same CSS variable hierarchy
- Viewport backgrounds now use CSS variables instead of hardcoded colors

**Validation:**
- Build passes successfully
- All themes (Dracula, Monokai, Solarized Dark, GitHub Dark, etc.) now have consistent terminal and tab backgrounds
- Both main home route and /inthome route have unified theming

## Recently Finished

-- Framework Enhancement:
- [✓] **Notification Service Integration** - Extract and generalize the NotificationService from `tests/integration/simpleeditor.tsx` into `src/icui/services/notificationService.tsx`. The current implementation in simpleeditor provides a clean pattern for toast notifications with auto-dismiss, multiple types (success, error, warning), and non-blocking UI feedback.

- [✓] **Backend Client Abstraction** - Create `src/icui/services/backendClient.tsx` base class based on the `EditorBackendClient` pattern from simpleeditor. Key features include connection status management, fallback mode handling, service availability detection, and consistent error handling across all backend operations.

- [] **File Management Service** - Extract file CRUD operations from simpleeditor into `src/icui/services/fileService.tsx`. Include language detection, workspace path management, auto-save with debouncing, and file modification tracking. The current implementation handles both ICPY and fallback modes effectively.

- [] **Theme Management Service** - Centralize theme detection logic from multiple editor components into `src/icui/services/themeService.tsx` with `useTheme()` hook. Both simpleeditor and ICUIEnhancedEditorPanel implement similar MutationObserver-based theme detection that should be unified.

- [] **Connection Status Components** - Create reusable connection status indicators based on the pattern in simpleeditor. Include visual connection state, error reporting, and refresh functionality for backend health monitoring.

- [] **Auto-save Framework** - Generalize the debounced auto-save pattern from simpleeditor into a reusable hook or service. Include configurable delays, modification tracking, and integration with notification system for save confirmations.



