## Project Overview
A web-based JavaScript code editor built with ViteReact, CodeMirror 6, and modern web technologies. The goal is to create a powerful, The world's most powerful notebook for developers, it includes 3 core parts: 1. rich text editor, similar to evernote/notion hybrid, 2. code editor + terminal, 3. AI agent that can be customized with agentic frameworks such as crew ai, or openai agent sdk, or any other agentic framework.

### In Progress
- [ ] Ready for next task

## Recently Finished
*Recently completed tasks have been moved to Working.md and roadmap_summaries.md for better organization.*

## Future task
- [] 
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



