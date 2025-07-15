# JavaScript Code Editor - Project Roadmap

## Project Overview
A web-based JavaScript code editor built with React, CodeMirror 6, and modern web technologies. The goal is to create a powerful, user-friendly code editor with real-time execution capabilities.

## In Progress
- [] (No current tasks in progress)

## Failed/Blocked Tasks

### Terminal Clipboard Implementation (FAILED)
- **Issue**: Terminal copy/paste functionality not working despite multiple implementation attempts
- **Attempts Made**: 
  1. Context menu with clipboard addon
  2. Auto-copy on selection with context menu
  3. Simplified keyboard shortcuts only
- **Root Cause**: Browser security restrictions prevent clipboard API access in current development environment
- **Status**: BLOCKED - requires HTTPS environment or alternative technical approach
- **Documentation**: See `docs/failed_context_imp.md` for detailed post-mortem
- **Recommendation**: Deprioritize until technical solution is found

## Future task
--terminal feature incomplete:
many super basic terminal features where not there such as:
tab auto complete for folders/directories.
ctrl + u to clean lines.
up key for last command.
and many more. one would assume a terminal would come with these features.

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


