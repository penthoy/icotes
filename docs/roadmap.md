## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create a powerful, The world's most powerful notebook for developers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal, 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework.

### In Progress

## Recently Finished

- [✓] work on integration_plan.md 2.3: Editor Integration, create a simpleeditor.tsx like the simpleterminal, using the simple reference icuieditorpanel from panels as a base, and then add it into App.tsx route - **COMPLETED with fallback mode for ICPY unavailability**

- [] we are at integration_plan.md 2.3: Editor Integration
- [] we are at icpy_plan.md 
- [] we are at icui_plan.md 4.10 clipboard, need to update 5 and beyond

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
## Future task

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

-- Framework Enhancement:
- [] **Notification Service Integration** - Extract and generalize the NotificationService from `tests/integration/simpleeditor.tsx` into `src/icui/services/ICUINotificationService.tsx`. The current implementation in simpleeditor provides a clean pattern for toast notifications with auto-dismiss, multiple types (success, error, warning), and non-blocking UI feedback.

- [] **Backend Client Abstraction** - Create `src/icui/services/ICUIBackendClient.tsx` base class based on the `EditorBackendClient` pattern from simpleeditor. Key features include connection status management, fallback mode handling, service availability detection, and consistent error handling across all backend operations.

- [] **File Management Service** - Extract file CRUD operations from simpleeditor into `src/icui/services/ICUIFileService.tsx`. Include language detection, workspace path management, auto-save with debouncing, and file modification tracking. The current implementation handles both ICPY and fallback modes effectively.

- [] **Theme Management Service** - Centralize theme detection logic from multiple editor components into `src/icui/services/ICUIThemeService.tsx` with `useICUITheme()` hook. Both simpleeditor and ICUIEnhancedEditorPanel implement similar MutationObserver-based theme detection that should be unified.

- [] **Connection Status Components** - Create reusable connection status indicators based on the pattern in simpleeditor. Include visual connection state, error reporting, and refresh functionality for backend health monitoring.

- [] **Auto-save Framework** - Generalize the debounced auto-save pattern from simpleeditor into a reusable hook or service. Include configurable delays, modification tracking, and integration with notification system for save confirmations.



