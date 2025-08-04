## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create the world's most powerful notebook for developers and hackers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal(similar to replit), 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework. This tool is designed to be infinitely hackable and flexible to empower the nextgeneration of AI powered developers.


### In Progress
- Currently no tasks in progress

### Todos before public release
- [] search for any hardcoding pathes.
- [] have a landing page
- [] able to use ollama
- [] add discord server
- [] build button that it can change itself and update itself with build button.
- [] chat should at least able to edit text files
such as the connection status from terminal.
- [] remove the Enhanced keyword from websocket enhancement
- [] add license
- [] add screenshot, and update readme
- [x] remove the duplicate uis from src/components/ui if they're under src/icui/components/ui
- [x] clean up the enhanced/Enhanced keyword: Search for the Enhanced word, I want to clean these up very conservatively, first search for it, analyze and give insight before change anything, and wait for my feedback.
- [x] make sure the enhanced version's features are fully integrated 
### Future tasks
- [] Feedbacks for agent_frontend plan:
1. those framework might be overkill:
2. design a .icotes folder in the root directory where it'll store any icotes related configs and infomation similar to .vscode, histories should be stored in .icotes/chat_history in .json format, design a schema that is optimized for simplicity and speed and flexibility. so that it is future proof in case plugins are added in the future or new capabilities added. so past chat histories will still be able to adapt.
3. add feature to measure agent context and token usage.

   e to have our agent make tool calls and do exactly what copilot agents do.
5. make sure these tools are easily extendable, tool creation are meant for humans to do which should be implemented as simple as possible and even a junior developer can do it, use our 3 personal agent as example on how it'll be done. make sure the backend does all the heavy lifting or build tooling and abstraction layers to make tool creation and custom agent creation very simple.

-- CLI/api
pip install typer fastapi of CLI that agents can work with
Able to open file in the editor with cli

- [] This api layer can also be used in the command line which also have hooks to the UI to do things like open a file in editor or have AI assistant use tools to edit file etc.
- api feature: detect what view is active so that the AI can have the correct context when you talk to it, it saves the state of the
- we'll add these endpoints later, but first we need to create a design document named api_plan.md in docs/plans folder and wait for me to review/edit it before proceed with building this layer.

-- Agents chat
1. AI can use tools, can edit files.
2. Proper history and new chat + button.
3. create tools: file/folder crud

-- bug:
Bug: Terminal press up and down or down and up, the cursor will go up and remove the previous line
Bug: I can ctrl + c to system memory but not from system memory to terminal

-- consolditate:
clean up docs folder,
clean up the enhanced keyword.
update documentation using a documentation library

look into backend/main.py and further abstract this code base.
Use icui menus
clean up unused routes in App.tsx

-- alpha deployment:
create docker image

--Features:
Explorer able to unlock Root path and go up and down different paths
json config for layouts
Drag and drop file and download file
learn and do playwright
icui: side tabs
icui: context menus
icui: drag and drop upload for future notebook for image, pdfs and media files.
Github and git integration
Rich text editor integration 

Add a settings menu under File menu
Add a custom sub menu under Layout, inside custom, there should be a save layout button, when clicked, it should give a popup to name your layout and click ok, once clicked it'll save the state of the current layout. as a new custom layout.

-- Explorer:
Real time update subscribe not working yet.

-- Editor:
Dragable tabs
Check state, if no state, Start blank no files are open, 
Save state: file that's opened previously should have their states saved this save 

-- Progressing on icui and icpy, need context right click menu
- [] work on integration_plan.md 6.5: Editor Integration, starting 7
- [] work on icpy_plan.md 
- [] work on icui_plan.md 7.1 clipboard, need to update 5 and beyond

-- Terminal
- [] Creating a new Terminal panel in the same area for example in the bottom, it'll look exactly the same as the other terminal, it seems like it is just displaying exactly what's in that terminal, this is the wrong behavior, if I create a new terminal panel at the top, it looks correct, please fix this, creating a new Terminal panel with the arrow drop down, regardless of where it was created, should be an independent terminal. this does for all other panels. not just the terminal.


-- Milestone 3:
Able to write simple software.
Refined Agent integration:
features: history, context
markdown for chat ui https://github.com/remarkjs/react-markdown
agent_plan.md
all tools created mirroring most agentic platform like copilot, cursor.
tool use indicator.
ouput copy button

-- Milestone 4:
Able to edit itself and improve itself with agentic features.
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
A Panel installer,
maya style code executor.
CLI should work similar to maya's, which later this will be for the nodes, similar to how nuke nodes would work.

## Recently Completed ✅
(Items moved to Working.md and CHANGELOG.md for reference)