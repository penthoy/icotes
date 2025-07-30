## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create the world's most powerful notebook for developers and hackers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal(similar to replit), 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework. This tool is designed to be infinitely hackable and flexible to empower the nextgeneration of AI powered developers.

### In Progress

### Recently Completed ✅

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

*Items are moved to Working.md and CHANGELOG.md once completed for historical reference*

