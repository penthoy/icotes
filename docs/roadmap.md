## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create the world's most powerful notebook for developers and hackers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal(similar to replit), 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework. This tool is designed to be infinitely hackable and flexible to empower the nextgeneration of AI powered developers.

### In Progress
- [✅] icpy phase 6(including step 6.5) is all complete, can you try to integrate it so that custom agents work?

### Recently Completed ✅
- ✅ **ICPY Phase 6.5: Custom Agent Integration Complete**:
  1. ✅ **Unified Chat Service Integration**: Custom agents now route through `/ws/chat` instead of separate endpoints
  2. ✅ **Three-Phase Streaming Protocol**: PersonalAgent, OpenAIDemoAgent, and OpenRouterAgent use START→CHUNKS→END protocol
  3. ✅ **Protocol Consistency**: Fixed async generator iteration in chat service for proper streaming
  4. ✅ **Backend Consolidation**: Removed deprecated `/api/custom-agents/chat` and `/ws/custom-agents/*/stream` endpoints  
  5. ✅ **Message Persistence**: All custom agent conversations saved to chat.db with session management
  6. ✅ **Agent Routing**: `agentType` metadata correctly routes messages to appropriate custom agents
  7. ✅ **Real-time Streaming**: Custom agents stream responses in real-time through unified chat service
  8. ✅ **Frontend Integration**: Dropdown selection and chat interface works seamlessly with all agent types
  9. ✅ **Step 6.5 Implementation**: Successfully integrated custom agent registry into unified chat service per icpy_plan.md
  - **Technical Achievement**: Custom agents fully integrated into unified streaming architecture with protocol consistency

## Future task
- [] please start on icpy_plan.md 6.4 and 6.5
-- bug:
✓ Bug: Terminal press up and down or down and up, the cursor will go up and remove the previous line

-- refactor enhanced ws endpoint in main.py

-- clipboard:
I can ctrl + c to system memory but not from system memory to terminal
-- Chat window:
Proper history and new chat + button.
✓ custom agent picker dropdown.

-- CLI
pip install typer fastapi of CLI
CLI that agents can work with
-- Milestone 2:
✓ home route refined and first mvp complete, can be showned.
critical features: you can start using your own APIs to create simple software.
Agents can edit files.
1. AI can use tools 
2. Custom agents that can self define agents in the agentic course.

-- consolditate:
clean up docs folder, clean up tests
There seems to be multiple ws endpoints clean up endpoints.
clean up the enhanced keyword.
clean up old icuiPanels
update documentation to use docu library
remove anything not being used under src/components/ui and src/components/archived
remove anything not being used under src/stories
look into backend/main.py and further abstract this code base.

--Features:
Explorer able to unlock Root path and go up and down different paths
json config for layouts
Drag and drop file and download file

-- Rich text editor integration (Phase 7)
-- Phase 7: Extension Points for Future Features
  - Service Discovery and Registry (7.1)
  - Plugin System Foundation (7.2) 
  - Authentication and Security Service (7.3)
  - Content Management Service Foundation (7.4)

-- Explorer:
Real time update subscribe not working yet.

-- Menus:
Use icui menus

-- Editor:
Dragable tabs
Check state, if no state, Start blank no files are open, 

-- backend cli:
Able to open file in the editor.
This CLI should work similar to maya's, which later this will be for the nodes, similar to how nuke nodes would work.


-- Progressing on icui and icpy, need context right click menu
- [] work on integration_plan.md 2.3: Editor Integration
- [] work on icpy_plan.md 
- [] work on icui_plan.md 7.1 clipboard, need to update 5 and beyond

- [] housekeeping, clean up unused routes in App.tsx

--Tool use for chat agents:
1. create tools: file/folder crud, 
-- Explorer/editor interaction:
Lets now attempt to replicate a modern editor behavior such as vs code:
1. ✓ when the page first loaded code editor should be empty.
2. ✓ When clicking on a text/script file in the explorer, it should temporily open in the editor and the name should be italic. if click on another text file immediate, the other file will replace that temporarilly opened file.
3. ✓ When double clicked on a text/script file it should open the file in "permenent" state, so when clicking on another file it will not be replaced, and the text on it will not be italic. this behavior is exactly the same as vs code.
4. save state: file that's opened previously should have their states saved this save 

please stop for my review for each of these points as it could be pretty complexe, and wait for my feedback before proceed for the next point, lets now start with 1.

-- Milestone 3:
Refined Agent integration:
features: history, context
markdown for chat ui https://github.com/remarkjs/react-markdown
agent_plan.md
all tools created mirroring most agentic platform like copilot, cursor.
tool use indicator.
ouput copy button

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

## Recently Completed ✅
- ✅ **Pytest Warnings Cleanup**: Reduced pytest warnings from 1599 to 33 (98% reduction) by:
  1. ✅ Added comprehensive pytest configuration with warning filters for external dependencies (CrewAI pkg_resources, Pydantic v1/v2, AST deprecations, etc.)
  2. ✅ Fixed all `datetime.utcnow()` deprecation warnings in codebase by updating to `datetime.now(timezone.utc)`
  3. ✅ Updated timezone handling in MemoryEntry and context management for proper datetime comparisons
  4. ✅ All 56 tests now pass with minimal warnings (only 33 dynamic/external warnings remain)
  5. ✅ **Technical Achievement**: Clean test output with 98% warning reduction, all core datetime deprecations eliminated

## Recently Finished
- ✅ **ICPY Plan Steps 6.1, 6.2, & 6.3 Completion**:
  1. ✅ **Step 6.1 Fixed**: Resolved CrewAI pkg_resources dependency issue by installing setuptools
  2. ✅ **Step 6.1 Verified**: All 8 agentic framework tests passing (OpenAI, CrewAI, LangChain, LangGraph compatibility)
  3. ✅ **Step 6.2 Confirmed**: All 28 agent workflow infrastructure tests passing
     - ✅ Agent workflow creation and execution infrastructure working
     - ✅ Capability registry system for skill discovery operational
     - ✅ Memory and context management system functional
     - ✅ Agent templates system for rapid development ready
     - ✅ All required files: base_agent.py, workflow_engine.py, capability_registry.py, context_manager.py, agent_templates.py
  4. ✅ **Step 6.3 Verified**: All 20 agent service layer tests passing
     - ✅ Agent lifecycle management and session handling working
     - ✅ Agent communication bus and task queue operational
     - ✅ Performance monitoring and resource management functional
     - ✅ API exposure through REST and WebSocket endpoints ready
     - ✅ Agent service fully integrated with workflow infrastructure

- ✅ **Custom Agent System Bug Fixes**:
  1. ✅ Fixed OpenAIDemoAgent giving demo responses - removed blank line at beginning of file that prevented proper import
  2. ✅ OpenAIDemoAgent now makes real OpenAI API calls and provides intelligent responses
  3. ✅ Integrated custom agents with chat service database for message history persistence
  4. ✅ Modified both HTTP and WebSocket endpoints to save user messages and agent responses to chat.db
  5. ✅ Added session management for custom agent conversations
  6. ✅ Both PersonalAgent and OpenAIDemoAgent now have full history support with database persistence
  7. ✅ Messages from custom agents are now properly saved and can be retrieved on page refresh
- ✅ **Custom Agent System Fixes**:
  1. ✅ Fixed tool calls in chat_stream in personal_agent.py - now properly handles tool execution during streaming
  2. ✅ Fixed history handling in custom agents - chat history is now correctly passed and processed
  3. ✅ Rewrote OpenAIDemoAgent to match personal_agent.py format with both chat() and chat_stream() functions
  4. ✅ Added OpenAIDemoAgent to custom_agent.py registry - now appears in frontend dropdown
  5. ✅ Both PersonalAgent and OpenAIDemoAgent now fully functional with streaming support
  6. ✅ Backend successfully loads both agents and handles API calls correctly
- ✅ **Custom Agent System Implementation**:
  1. ✅ Rewrote custom_agent.py to be simple (under 50 lines) - now acts as an entry point and registry for custom agents
  2. ✅ Updated main.py to use the new custom_agent.py structure with new `/api/custom-agents/chat` endpoint 
  3. ✅ Enhanced ICUIChat.tsx frontend to include personal_agent.py chat function as dropdown menu option
  4. ✅ Added sendCustomAgentMessage function to useChatMessages hook to handle custom agent API calls
  5. ✅ Implemented gradio-like chat function capability that can take user-defined chat functions
  6. ✅ Successfully tested PersonalAgent integration - custom agent registry working correctly
  7. ✅ Frontend build verification completed - all TypeScript compilation successful

-- Milestone 1:
✓ Complete icui-icpy connection and integration plan so that the old home route is using icpy backend.

- ✓ **main.py refactoring completed (Phase 2)**:
1. ✓ Removed all legacy endpoints: legacy_websocket_endpoint, ConnectionManager, duplicate terminal endpoints (6 endpoints: POST /api/terminals, GET /api/terminals, GET /api/terminals/{id}, POST /api/terminals/{id}/start, DELETE /api/terminals/{id}, POST /api/terminals/{id}/input)
2. ✓ Organized configuration code into functions: initialize_rest_api(), configure_cors_origins(), mount_static_files()  
3. ✓ Removed endpoint duplication - icpy REST API already provides comprehensive terminal endpoints, making main.py duplicates redundant
4. ✓ All remaining endpoints verified as actively used by frontend: /clipboard (POST/GET), /clipboard/history, /clipboard/status, /clipboard/clear, /execute, /api/custom-agents, /health, WebSocket endpoints
5. ✓ Maintained clean separation: configuration in functions, core endpoints preserved, icpy integration intact
6. ✓ Build and syntax validation passed - reduced main.py from 1135 to 958 lines (177 lines removed)
- ✓ Refactored main.py in backend:
1. Reduced file size from 1441 lines to 1204 lines (237 lines removed)
2. Removed duplicate ServerClipboard class and consolidated with icpy clipboard service
3. Moved all imports to the top of the file with proper error handling
4. Maintained try-except for imports where necessary for graceful fallbacks
5. Fixed demo_agent import to be conditional to prevent import errors
6. All functionality preserved and tested working

✅ Bug fix: tab shouldn't reload after switched

✅ **ICUI Panel Tab and Drag/Drop Bug Fixes**
- **Panel Tab Persistence Bug**: Fixed issue where tab content would reload/unload when switching between tabs in ICUITabContainer.tsx - tabs now properly persist their content state like VS Code tabs
- **Panel Drag/Drop Infinite Loop**: Fixed infinite loop in panel drag/drop operations by adding defensive checks in ICUIEnhancedLayout.tsx and ICUIEnhancedPanelArea.tsx to prevent drag enter/leave events from cascading between containers
- **Build Verification**: Confirmed all changes compile successfully with TypeScript and Vite build process
- **Technical Achievement**: Panel tabs now persist their state (like Editor tabs), and drag operations are stable without causing infinite loops between panel containers

✅ **Terminal Arrow Key Navigation Bug Fix** 
- **Root Cause**: WebSocket URL mismatch - ICUITerminal was using `/terminal/` endpoint when environment variable was set, but backend expects `/ws/terminal/` path
- **Fix Applied**: Updated ICUITerminal.tsx WebSocket URL construction to use `/ws/terminal/` path consistently, matching the working SimpleTerminal implementation
- **Terminal Configuration**: Simplified terminal options to match working SimpleTerminal configuration, removing potentially interfering options like `altClickMovesCursor`, `convertEol`, etc.
- **Build Verification**: Confirmed successful compilation and build process
- **Technical Achievement**: ICUITerminal arrow key navigation should now work correctly for command history, matching VS Code terminal behavior

✅ **Custom Agent Dropdown Implementation**
- **Frontend Dropdown Component**: Created `CustomAgentDropdown.tsx` component following GitHub Copilot's agent selector design pattern
- **Agent API Integration**: Implemented `useCustomAgents.ts` hook to fetch available custom agents from `/api/agents/custom` endpoint
- **ICUIChat Integration**: Added custom agent selection dropdown to main `ICUIChat.tsx` component below message input with GitHub Copilot-style design
- **SimpleChat Integration**: Added custom agent selection dropdown to SimpleChat interface with real-time agent switching
- **UI/UX Features**: 
  1. Loading states with spinner animation
  2. Error handling with visual feedback
  3. GitHub Copilot-style design with gradient icons and consistent styling
  4. Agent selection persistence during chat sessions
  5. Disabled state when disconnected from backend
  6. ICUI CSS variable integration for theme consistency
- **Agent Message Routing**: Updated message sending to include selected agent type in MessageOptions for proper backend routing
- **Theme Support**: Full dark/light theme compatibility using existing ICUI CSS variables

✅ **Custom Agent Architecture Abstraction**
- **Backend Abstraction**: Successfully abstracted `auto_initialize_chat_agent()` function from `main.py` to `backend/icpy/agent/custom_agent.py`
- **Agent Base Class**: Created `CustomAgentBase` abstract class with standardized chat input/output interface (`process_chat_input`, `process_chat_stream`)
- **OpenAI Demo Agent**: Implemented `OpenAIDemoAgent` class demonstrating the custom agent framework with support for:
  1. Chat input processing with context support
  2. Streaming response capabilities 
  3. Tool/function calling framework integration ready
  4. Support for OpenAI SDK, CrewAI, and LangChain/LangGraph (foundation laid)
- **Frontend Integration**: Added `/api/agents/custom` endpoint to expose available custom agents for frontend dropdown menu
- **Agent Registry**: Implemented `CUSTOM_AGENTS` list and factory functions (`get_available_custom_agents`, `create_custom_agent`)
- **Architecture**: Clean separation of concerns with custom agents having standardized interface for chat input → chat output workflow

✅ **ICUIChat.tsx Component Implementation**
- Created new `ICUIChat.tsx` component following the established ICUI framework patterns
- **Component Structure**: Implemented using forwardRef pattern similar to `ICUITerminal.tsx`, `ICUIExplorer.tsx`, and `ICUIEditor.tsx`
- **Backend Integration**: Integrated with `useChatMessages` hook for real-time chat functionality with ICPY backend
- **Theme Support**: Added full theme detection and ICUI CSS variable support for consistent styling
- **Features**: Auto-scroll, connection status monitoring, message history, copy/paste functionality, keyboard shortcuts
- **Type Safety**: Full TypeScript support with `ICUIChatRef` interface for imperative control
- **Home Integration**: Successfully replaced `ICUIChatPanel.tsx` with the new component in `home.tsx`
- **Export Setup**: Added proper exports to ICUI framework index for seamless integration
- **Build Validation**: Confirmed successful compilation and build process
- **UI Improvements**: 
  - Enhanced chat bubble styling with dimmer user message colors using subtle gray themes instead of bright accent colors
  - Maximized screen real estate by increasing chat bubble width from 80% to 95% for better coding assistant experience
  - Added subtle border styling to distinguish user messages while maintaining theme consistency

**Phase 6 COMPLETE**: All agentic backend infrastructure is production-ready with real API integration, comprehensive testing, full chat service support, and fully functional frontend integration at `/simple-chat`.

✅ **Streaming Chat Duplicate Response Fix** 
- Fixed duplicate message issue in SimpleChat where streaming and complete responses appeared simultaneously
- **Backend Fix**: Modified `_execute_streaming_agent_task` to handle errors within streaming context instead of sending separate complete messages
- **Frontend Fix**: Enhanced React message handling to prevent duplicate keys by checking existing message IDs and properly handling streaming vs complete message states
- **Root Cause**: Backend was sending both streaming chunks AND complete error responses, while frontend was adding duplicate entries for same message ID
- **Result**: Only streaming responses are now displayed during live chat, with proper database persistence for message history

✅ **ICPY Phase 6: Complete Agentic Backend + Frontend Integration** 
- icpy_plan.md 6.1 (Framework Installation & Setup) 
- icpy_plan.md 6.2 (Agentic Workflow Infrastructure)
- icpy_plan.md 6.3 (Agent Service Layer)  
- icpy_plan.md 6.4 (Chat Service Implementation)
- Frontend Integration: SimpleChat Production Implementation ✅
- REST API Integration: All endpoints functional ✅
- WebSocket + HTTP API: Full production integration ✅

-- ICPY Step 6.1: Agentic Framework Installation and Validation:
- [✓] **Agentic Framework Installation and Validation** - Successfully installed and validated all core agentic frameworks:
  1. ✓ **Framework Installation**: Installed OpenAI SDK (1.97.1), CrewAI (0.150.0), LangChain (0.3.27), and LangGraph using `uv` package manager
  2. ✓ **Framework Compatibility Layer**: Created unified interface in `backend/icpy/core/framework_compatibility.py` with consistent API across all frameworks
  3. ✓ **Agent Creation and Validation**: Implemented agent wrappers for all frameworks with creation, execution, streaming, and lifecycle management
  4. ✓ **Cross-Framework Testing**: Created comprehensive test suite with 8 passing tests validating framework imports, agent creation, and error handling
  5. ✓ **Async Support**: Added full async/await compatibility and streaming execution for all frameworks
  6. ✓ **Documentation Update**: Updated backend README.md to use `uv` package manager for faster dependency management
  7. ✓ **Validation Script**: Created `validate_step_6_1.py` demonstrating complete framework functionality
  - **Technical Achievement**: All frameworks working with unified interfaces, ready for Step 6.2 workflow infrastructure

-- ICPY Plan Agentic Foundation Documentation:
- [✓] **Phase 6 Agentic Foundation Specification** - Completed detailed documentation for icpy_plan.md sections 6.1, 6.2, and 6.3:
  1. ✓ **Step 6.1: Agentic Framework Installation and Validation** - Comprehensive plan for installing OpenAI Agent SDK, CrewAI, LangChain/LangGraph with framework compatibility layer and validation testing
  2. ✓ **Step 6.2: Agentic Workflow Infrastructure** - Detailed structure for `backend/icpy/agent/` directory organization including base agent interface, workflow definitions, configuration templates, and execution engine
  3. ✓ **Step 6.3: Agent Service Layer Implementation** - Complete specification for agent service layer with lifecycle management, communication bus, task scheduling, and API exposure
  4. ✓ Maintained consistency with existing icpy_plan.md documentation style and depth
  5. ✓ Integrated with existing Phase 6.4 Chat Service requirements for complete agentic foundation
  6. ✓ Added comprehensive integration test specifications for each step
  - **Technical Coverage**: Framework installation validation, workflow infrastructure setup, agent service implementation, API integration, and real-time event streaming

-- Simple Chat Component Implementation:
- [✓] **SimpleChat.tsx Component** - Created a minimal chat interface for agentic interaction:
  1. ✓ Implemented simplechat.tsx following the same pattern as simpleeditor, simpleexplorer, and simpleterminal
  2. ✓ Added WebSocket connection to `/ws/chat` for real-time bidirectional messaging
  3. ✓ Integrated HTTP REST endpoints for message history, chat config, and agent status
  4. ✓ Added support for message persistence with proper metadata handling
  5. ✓ Implemented connection status monitoring with visual feedback
  6. ✓ Added theme-aware styling with automatic dark/light mode detection
  7. ✓ Created notification system for user feedback on connection status
  8. ✓ Added route `/simple-chat` to App.tsx for easy access
  9. ✓ **Backend Requirements Specification**: Completed icpy_plan.md section 6.4 defining chat service requirements from frontend perspective including WebSocket endpoints, HTTP APIs, message persistence, agent integration, and error handling specifications for backend implementation
  - **Technical Features**: Auto-scroll, typing indicators, message threading, error recovery, agent capability reporting, clipboard integration compatibility

-- Cloudflare Tunnel Compatibility:
- [✓] **Smart Domain Detection for Backend Connections** - Fixed Code Editor connectivity issues with Cloudflare tunnels:
  1. ✓ Analyzed connection patterns across Terminal, Explorer, and Editor components
  2. ✓ Identified that Terminal and Explorer worked due to fallback mechanisms, while Editor used hardcoded IP addresses
  3. ✓ Implemented smart domain detection logic in all backend client classes
  4. ✓ Added automatic fallback to dynamic URL construction when accessing through different domains (e.g., Cloudflare tunnels)
  5. ✓ Updated ICUIEditor, BackendConnectedEditor, BackendConnectedExplorer, ICUIExplorer, BackendConnectedTerminal, ICUIBaseFooter, simpleeditor, and backendClient components
  6. ✓ Enhanced logging for debugging domain detection and URL construction
  7. ✓ Verified build compatibility - all components now work with both direct IP access and Cloudflare tunnel domains
  - **Technical Implementation**: Components now compare `window.location.host` with configured .env URLs and automatically switch to dynamic construction when domains don't match, ensuring seamless operation across different access methods

-- Explorer Real-time Updates:
- [✓] **Real-time File System Monitoring** - Implemented automatic Explorer updates when files/folders change externally:
  1. ✓ Integrated WebSocket service with ICUIExplorer for real-time event listening
  2. ✓ Added subscription to filesystem events (fs.file_created, fs.file_deleted, fs.file_moved)
  3. ✓ Implemented event filtering to only respond to changes within current workspace
  4. ✓ Added debounced refresh (300ms) to prevent excessive updates from rapid file operations
  5. ✓ Maintained Explorer performance by only refreshing on structural changes (not content modifications)
  6. ✓ Enhanced debugging with console logging for filesystem events
  7. ✓ Leveraged existing backend file watching infrastructure (watchdog + message broker)
  - Explorer now automatically reflects external file/folder changes without manual refresh

-- Explorer Enhancement:
- [✓] **VS Code-like Explorer Behavior** - Updated ICUIExplorer to use tree-like folder expansion instead of navigation:
  1. ✓ Modified folder click behavior to expand/collapse folders in place instead of navigating into them
  2. ✓ Implemented tree structure with proper nesting and indentation (16px per level)
  3. ✓ Added expand/collapse icons (>/v) for folders with visual feedback
  4. ✓ Updated folder icons to show open/closed state (📁/📂)
  5. ✓ Implemented on-demand loading of folder contents when expanded for the first time
  6. ✓ Added recursive tree rendering with proper parent-child relationships
  7. ✓ Maintained file selection and context menu functionality
  8. ✓ Preserved existing file operations (create, delete) while improving folder navigation
  9. ✓ **Added intelligent sorting**: Folders always appear first, followed by files (both sorted alphabetically)
  10. ✓ Fixed infinite loop issues with proper functional state updates
  - The explorer now behaves like VS Code's file explorer with hierarchical folder structure and proper sorting

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

-- Editor Tab Management:
- [✓] **Tab Switching Without Reload** - FIXED: Completely redesigned tab switching mechanism in ICUIEditor to eliminate unnecessary editor recreation:
  1. ✓ Editor instance now persists across tab switches - only recreated on theme changes, not file changes
  2. ✓ Content switching uses CodeMirror's dispatch API to update editor content without destroying the editor
  3. ✓ Preserved editor state (cursor position, scroll position, undo history) when switching between tabs
  4. ✓ Improved state synchronization to save current editor content before switching to new file
  5. ✓ Enhanced memory efficiency by keeping all opened tabs in memory without reload
- [✓] **Tab Close Button Bug** - FIXED: Resolved issue where clicking "X" to close a tab would reopen when clicking another tab:
  1. ✓ Improved file state management to properly remove closed files from the files array
  2. ✓ Enhanced active file switching logic to handle edge cases when no files remain
  3. ✓ Added proper content preservation before closing to prevent data loss
  4. ✓ Fixed confirmation dialog to use the most current editor content for save prompts
  5. ✓ Ensured closed files are permanently removed and don't reappear during tab navigation

