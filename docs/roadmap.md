## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create the world's most powerful notebook for developers and hackers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal(similar to replit), 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework. This tool is designed to be infinitely hackable and flexible to empower the nextgeneration of AI powered developers.

### In Progress

## Future task

-- editor:
- [] Switching tabs should not reload the file or the whole tab, and swithing to other tab it should stay.
- [] Bug: clicking on x close the tab, but clicking on another tab opens it back up, this should not be the case.

-- Explorer:
clicking on folder/directories should not go inside the directory

-- Explorer/editor interaction:
When clicking on a text/script file in the explorer, it should temporily open in the editor
-- integration 2.5:
Now that explorer, code editor and terminal works, next is how they talk to each other.
1. Editor:remove the Connected area, there's no need for editor to show connection independently.
2. Remove the top 2 bars and add bottom bar, the auto save popup is too intrusive, it should be very subtle but it on the bottom bar that should say something like saving...
- [] Update integration details: explorer is empty by defaul, but populates 
3. use src/icui/menus on inthome.tsx

-- backend cli:
Able to open file in the editor.
when clicking on files in the explorer, under the hood it should also just do this.
This CLI should work similar to maya's, which later this will be fore the nodes, similar to how nuke nodes would work.

-- Chat window:
same function as what copilot window has

-- Progressing on icui and icpy, need context right click menu
- [] work on integration_plan.md 2.3: Editor Integration
- [] work on icpy_plan.md 
- [] work on icui_plan.md 7.1 clipboard, need to update 5 and beyond

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

-- Milestone 6:
Beyond copilot: these features are designed to be simple enough to implement but what copilot/cursor/winsurf users would want:
1. Qued execution, these are notebooks with detailed instructions that you can write and can execute in the background.
2. Tickets: you can task the agent to compartmentalize their role, for example one Agent can only take care of the frontend while the other only does the backend, so they are ok to have limited context, and build in soft guardrails so they only operate within their folder structures, if the frontend agent require something from the backend, they write a ticket to the backend, and the backend can pick it up, its like a hand-off but they're human readable, and can be intercepted by human for oversight.
3. node graph, a flexible Node panel that can be used like n8n 

-- Milestone 7:
AI Agents writing complex AI agents.
types: bird's eye view agent, overseer, one that looks at the overview of the entire project, without knowing too much detail.
types: insight/distill agent. one that takes note on the 
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

-- Home Route Migration:
- [✓] **IntHome to Home Migration** - Successfully migrated inthome.tsx to replace the current home.tsx:
  1. ✓ Renamed current home.tsx to home_deprecate.tsx
  2. ✓ Copied inthome.tsx to home.tsx and updated import paths
  3. ✓ Copied all dependencies (BackendConnectedEditor, BackendConnectedExplorer, BackendConnectedTerminal) to src/icui/components/
  4. ✓ Updated component name from IntegratedHome to Home with proper props interface
  5. ✓ Verified build success - new home route is working properly
  6. ✓ Removed floating UI elements (Backend Connected status and workspace path indicators)
  7. ✓ Combined editor status bars: merged connection status with file info bar, removed redundant refresh button and file type display, now shows full file path for better context
  8. ✓ Consolidated connection status: replaced non-functional bottom-right "Connected" status with real connection status from BackendConnectedEditor, moved connection status display from editor area to bottom-right footer for cleaner editor interface while maintaining single source of truth for backend connectivity

-- Framework Enhancement:
- [✓] **Notification Service Integration** - Extract and generalize the NotificationService from `tests/integration/simpleeditor.tsx` into `src/icui/services/notificationService.tsx`. The current implementation in simpleeditor provides a clean pattern for toast notifications with auto-dismiss, multiple types (success, error, warning), and non-blocking UI feedback.

- [✓] **Backend Client Abstraction** - Create `src/icui/services/backendClient.tsx` base class based on the `EditorBackendClient` pattern from simpleeditor. Key features include connection status management, fallback mode handling, service availability detection, and consistent error handling across all backend operations.

- [] **File Management Service** - Extract file CRUD operations from simpleeditor into `src/icui/services/fileService.tsx`. Include language detection, workspace path management, auto-save with debouncing, and file modification tracking. The current implementation handles both ICPY and fallback modes effectively.

- [] **Theme Management Service** - Centralize theme detection logic from multiple editor components into `src/icui/services/themeService.tsx` with `useTheme()` hook. Both simpleeditor and ICUIEnhancedEditorPanel implement similar MutationObserver-based theme detection that should be unified.

- [] **Connection Status Components** - Create reusable connection status indicators based on the pattern in simpleeditor. Include visual connection state, error reporting, and refresh functionality for backend health monitoring.

- [] **Auto-save Framework** - Generalize the debounced auto-save pattern from simpleeditor into a reusable hook or service. Include configurable delays, modification tracking, and integration with notification system for save confirmations.

-- Theme fix:
- [✓] terminal theme looking wrong, the background color should match rest of the other panels - FIXED: Terminal now uses CSS variables (--icui-bg-primary) for background to match other panels
- [✓] Monokai and one Dark theme is wronge most aparently on the editor tabs - FIXED: Active tabs now use lighter colors (--icui-bg-tertiary) instead of darker colors for all dark themes
- [✓] editor tab color is wrong, the active tab should have lighter instead of darker color and should be the same color as the panel tabs - FIXED: Both ICUI framework tabs and BackendConnectedEditor tabs now use consistent ICUI CSS variables and proper color hierarchy

-- Bug fix:
- [✓] Editor: no scroll bar - FIXED: Added proper overflow handling to CodeMirror editor with overflow: 'auto' on .cm-scroller and proper height constraints on .cm-editor and .cm-content to enable vertical scrolling when content exceeds visible area

