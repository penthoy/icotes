# JavaScript Code Editor - Project Roadmap

## Project Overview
A web-based JavaScript code editor built with React, CodeMirror 6, and modern web technologies. The goal is to create a powerful, user-friendly code editor with real-time execution capabilities.

## In Progress 🚧
- [] Cleanup: remove anything under the following directories so that 
- [] 

## Future tasks:
- [] Backend: refactor the main.py and create a terminal.py move everything terminal related from main.py to terminal.py so that it is more modular.

- [] Add agent chat tab on the left side same place as the Explorer with a tab, similar to how vs code extensions are installed on the left side.

## Recently Finished 🎉
- [x] **Updated Development Script to Single-Port Architecture**: Updated start-dev.sh to match production setup:
  - **Root Cause**: start-dev.sh was using outdated dual-port setup (frontend on 5174, backend on 8000)
  - **Solution**: Updated start-dev.sh to match start.sh single-port architecture
  - **Single Port Setup**: Both development and production now use port 8000 for unified access
  - **Script Consistency**: start-dev.sh now builds frontend and serves it from backend, matching production
  - **Environment Variables**: Proper environment variable handling for consistent configuration
  - **Package.json Updates**: Updated npm scripts to use uvicorn instead of direct python main.py calls
  - **Development Experience**: Simplified development setup with consistent port usage

- [x] **Enhanced Terminal Bottom Boundary Detection**: Fixed terminal scrolling and container boundaries:
  - **Root Cause**: Terminal was not properly detecting container boundaries causing content overflow
  - **Enhanced Fitting Logic**: Added more aggressive terminal fitting with multiple retry attempts
  - **Improved Resize Detection**: Enhanced ResizeObserver with proper debouncing and logging
  - **Container Constraints**: Added explicit height and overflow constraints to terminal containers
  - **CSS Improvements**: Added comprehensive CSS rules for xterm viewport, screen, and rows
  - **Debug Logging**: Added detailed logging for container dimensions and terminal sizing
  - **Multiple Fit Attempts**: Terminal now attempts to fit multiple times during initialization
  - **Scroll Configuration**: Enhanced terminal scroll settings for better user experience
- [x] **Frontend UI Terminal Bottom Boundary Fix**: Fixed terminal not detecting bottom boundary causing output to disappear:
  - **Root Cause**: Terminal container did not have proper height constraints and positioning
  - **Solution**: Updated XTerminal component with proper CSS styling and height management
  - **Improved Layout**: Added absolute positioning with proper flex layout for better container management
  - **Enhanced Scrolling**: Added proper overflow handling to prevent content from disappearing
  - **CSS Improvements**: Added custom CSS rules for terminal viewport to ensure proper height and scrolling behavior
  - **Container Styling**: Added minimum height constraints to ensure terminal is always visible
  - **Background Color**: Added proper background color to ensure terminal content is visible

- [x] **Flexible UI Panel System**: Enhanced panel system to be more flexible like VS Code:
  - **ResizablePanel Enhancement**: Added collapse/expand functionality with visual controls
  - **Maximizable Panels**: Added maximize/restore functionality for panels to fill entire screen
  - **VerticalResizablePanel Enhancement**: Added similar collapse/expand and maximize features for vertical panels
  - **Control Buttons**: Added intuitive control buttons (ChevronLeft/Right, Maximize/Minimize icons)
  - **State Management**: Proper state management for collapsed/expanded and maximized states
  - **Callback Functions**: Added callback functions for external state synchronization
  - **Flexible Border Expansion**: Panels can now expand to fill available space more flexibly
  - **VS Code-like Experience**: Panel behavior now mimics VS Code's flexible panel system

- [x] **V Panel Arrow Button Bug Fix**: Fixed panel disappearing issue when arrow button is clicked:
  - **Root Cause**: Panel state was not properly synchronized between internal and external state
  - **Solution**: Added useEffect to sync internal isPanelOpen state with external isVisible prop
  - **State Synchronization**: Proper state management to prevent panel from disappearing permanently
  - **Toggle Functionality**: Fixed toggle behavior to properly show/hide panels
  - **Recovery Mechanism**: Panel can now be restored without requiring a page refresh
  - **Improved UX**: Added proper titles and tooltips for better user experience
- [x] **Enhanced port configuration for flexible deployment**: Improved deployment compatibility across different platforms:
  - **Flexible Port Detection**: Application now supports both `PORT` and `BACKEND_PORT` environment variables
  - **Platform Compatibility**: Automatic port detection for Coolify, Railway, Render, and other containerized platforms
  - **Priority System**: `BACKEND_PORT` takes precedence over `PORT` for manual deployments
  - **Logging Enhancement**: Added detailed logging for port configuration debugging
  - **Documentation**: Created comprehensive port configuration guide
  - **Environment Variables**: Updated all deployment scripts to support multiple port configuration methods
  - **Coolify Integration**: Seamless integration with Coolify's automatic port assignment
  - **Container Support**: Enhanced Docker and container deployment compatibility
- [x] **Fixed production frontend serving**: Resolved frontend access issues in production deployment:
  - **Single Port Architecture**: Frontend now properly served from backend at port 8000
  - **Static File Serving**: Implemented proper static file serving for React build assets
  - **SPA Routing**: Added catch-all route for client-side routing support
  - **FileResponse Integration**: Proper file serving with correct MIME types
  - **Asset Mounting**: Configured `/assets` route for CSS and JavaScript files
  - **Development Fallback**: Graceful fallback when frontend build is not available
  - **Clear Instructions**: Updated start.sh script with proper access URLs
  - **Production Testing**: Verified frontend accessibility at `http://your-ip:8000`
- [x] Fixed Deployment issue now with start.sh
- [x] Fix Terminal \x1b[32mConnecting to terminal...\x1b[0m\r\n\x1b[36mTerminal ID: 0jwyk9\x1b[0m\r
- [x] Fix Terminal speed issue
- ✅ **Fixed frontend-backend connection issues**: Resolved connectivity problems between frontend and backend:
  - **Root Cause**: Frontend development server was binding to localhost instead of network IP address
  - **Environment Variables**: Updated scripts to properly load and pass environment variables to Vite
  - **Network Binding**: Frontend now correctly binds to `192.168.2.195:5173` instead of `localhost:5173`
  - **Proxy Configuration**: Verified proxy settings in `vite.config.ts` work correctly with environment variables
  - **Development Scripts**: Created comprehensive `start-dev-env.sh` script with proper environment variable handling
  - **Updated start-dev.sh**: Modified existing script to pass VITE environment variables to frontend
  - **Connection Verification**: Both frontend and backend now properly accessible at configured IP addresses
  - **API Connectivity**: Confirmed `/health`, `/execute`, and WebSocket endpoints work correctly
  - **Production Build**: Environment variables now properly embedded in production builds via `.env.production`

- ✅ **Cleaned up tempo-specific code and dependencies**: Removed all tempo-related code that was not being used in the core project:
  - Removed tempo-devtools import and initialization from `src/main.tsx`
  - Removed tempo-routes import and conditional rendering from `src/App.tsx`
  - Removed tempo-devtools dependency from `package.json`
  - Removed tempo plugin from `vite.config.ts` and cleaned up optimizeDeps
  - Deleted tempo-specific configuration files (`tempo.config.json`, `start-tempo.sh`)
  - Removed tempo-specific documentation (`docs/tempo_deployment.md`)
  - Cleaned up empty `src/tempobook` directory
  - Modified `docs/single_port_solution.md` to remove tempo-specific references while preserving valuable single-port architecture documentation
  - Verified application builds and runs successfully after cleanup
  - Maintained clean, focused codebase for the core JavaScript code editor functionality

- ✅ **Fixed terminal connection for Tempo environment constraint**: Completely resolved WebSocket connection issues in the Tempo remote development environment:
  - **Root Cause Identified**: Application was running in development mode (Vite dev server) while WebSocket tried to connect to same host/port
  - **Production Mode Solution**: Modified default deployment to run production build where FastAPI serves everything on one port  
  - **Single-Port Architecture**: FastAPI backend now serves both React app static files AND WebSocket endpoints
  - **Dynamic URL Construction**: Frontend automatically constructs WebSocket URLs using current page's host/port (`window.location.host`)
  - **Environment Variable Support**: Backend uses PORT environment variable for flexible deployment
  - **Tempo-Specific Scripts**: Created `start-tempo.sh` and updated `npm run dev` for production deployment
  - **Verified Solution**: Tested complete build → deploy → connect workflow successfully
  - **No More Connection Errors**: WebSocket terminals now connect to `wss://your-app.tempo-dev.app/ws/terminal/{id}` correctly
  - **Comprehensive Documentation**: Created detailed deployment instructions in `/app/docs/tempo_deployment.md`
- [] Add agent chat tab on the left side same place as the Explorer with a tab, similar to how vs code extensions are installed on the left side.

## Recently Finished 🎉
- ✅ **Fixed terminal layout and scrolling issues**: Improved the terminal and overall application layout:
  - Changed main container from min-h-screen to h-screen for proper viewport sizing
  - Added overflow-hidden to prevent double scrollbars
  - Implemented proper flex layout with flex-shrink-0 for fixed elements
  - Added custom scrollbar styling for xterm.js that matches the theme
  - Terminal now automatically resizes to fit container with ResizeObserver
  - Eliminated page-level scrolling in favor of terminal-only scrolling
  - Custom CSS for xterm viewport scrollbars with theme-aware colors

- ✅ **Updated terminal tab system with multiple tabs support**: Enhanced the terminal interface with a dynamic tab system:
  - Terminal tab is now the default and only tab open by default
  - Added + icon in the tab panel to create additional tabs
  - Support for both Terminal and Output tab types
  - Closable tabs with X button (except the first terminal tab)
  - Improved tab management with proper state handling
  - Better visual design with hover effects and proper spacing

- ✅ **Implemented a real terminal with PTY support**: Enhanced the terminal functionality with proper PTY-based terminal emulation:
  - Integrated xterm.js for professional terminal emulation in the browser
  - Added backend PTY (pseudoterminal) support using Python's pty module
  - Created WebSocket-based communication between frontend and backend terminal sessions
  - Implemented proper terminal session management with unique terminal IDs
  - Added terminal resizing support and proper cleanup on disconnect
  - Created XTerminal component with connection status indicators and controls
  - Added terminal reconnection capabilities and error handling
  - Integrated terminal into the existing tabbed output panel interface
  - Each terminal session runs in an isolated bash shell environment

- ✅ **Created comprehensive system architecture documentation**: Designed and documented the complete system architecture:
  - Detailed current architecture overview (Vite frontend + FastAPI backend)
  - Component-level architecture diagrams and explanations
  - Data flow documentation with sequence diagrams
  - Security considerations and current limitations
  - Performance optimization strategies
  - Scalability design patterns
  - Future architecture roadmap (v2.0+ with Rust backend)
  - Deployment architecture and production considerations
  - Technology decision rationale and trade-offs
  - Monitoring and observability planning

- ✅ **Added FastAPI backend with WebSocket support**: Created a complete backend infrastructure:
  - FastAPI server with CORS support for cross-origin requests
  - Real-time WebSocket communication for code execution
  - REST API endpoints for code execution and health monitoring
  - Python code execution with output and error capture
  - Comprehensive error handling and logging
  - Connection management and reconnection logic
  - Fallback from WebSocket to REST API if connection fails

- ✅ **Created WebSocket frontend integration**: Enhanced frontend with real-time backend communication:
  - CodeExecutor utility class with WebSocket and REST API support
  - Automatic connection management and reconnection logic
  - Real-time code execution with proper error handling
  - Execution time tracking and performance monitoring
  - Seamless fallback between WebSocket and REST API
  - Updated UI with execution status indicators

- ✅ **Made the terminal resizable**: Enhanced the terminal/output panel with vertical resizing capabilities:
  - Created VerticalResizablePanel component for vertical resizing functionality
  - Added drag handle at the top of the terminal panel for resizing
  - Configurable minimum height (100px) and maximum height (600px)
  - Smooth mouse interaction with proper cursor changes during resize
  - Integrated resizable panel into the main layout while maintaining existing functionality
  - Terminal can now be resized vertically by dragging the top border

- ✅ **Added proper terminal with tabs in output area**: Implemented a VSCode-like tabbed interface for the bottom panel with:
  - Output tab: Shows code execution results and errors (existing functionality)
  - Terminal tab: Interactive command-line interface with:
    - Command history (up/down arrows)
    - Built-in commands (help, clear, echo, date)
    - Terminal-style UI with green text on black background
    - Proper scrolling and auto-focus
  - Tabbed interface with smooth switching between Output and Terminal
  - Consistent styling and theme integration

- ✅ **Added Python support as default language**: Enhanced the code editor with multi-language support:
  - Installed @codemirror/lang-python for Python syntax highlighting
  - Updated default file from main.js to main.py
  - Added language detection based on file extensions (.py, .js, .jsx)
  - Automatic language switching when switching between files
  - Python code execution simulation (basic print statement parsing)
  - Updated new file creation to default to Python (.py extension)
  - Proper Python syntax highlighting and code completion

- ✅ **Fixed Output panel layout**: The output panel was incorrectly positioned to the right of the code editor horizontally. Fixed by:
  - Restructuring the layout to position the output panel below the code editor vertically
  - Maintaining the explorer sidebar on the left
  - Creating a proper VSCode-like layout with file tabs, editor, and output panel stacked vertically
  - Ensuring the output panel remains collapsible and functional

- ✅ **Fixed cursor disappearing issue**: The cursor would disappear after typing each character, requiring manual mouse clicks to continue typing. This was caused by the CodeMirror editor being recreated on every keystroke. Fixed by:
  - Separating editor initialization from content updates
  - Using transactions to update editor content instead of recreating the entire editor
  - Only recreating the editor when theme changes, not on content changes
  
- ✅ **Added VSCode-like file explorer sidebar**: Implemented a resizable file explorer on the left side with:
  - File tree structure with folders and files
  - File icons based on file extensions
  - Context menu for file operations (create, rename, delete)
  - Resizable panel that can be toggled on/off
  - Integration with existing file tabs system
  - Toggle button in header to show/hide explorer

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
- ✅ Tempo platform integration for development

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
