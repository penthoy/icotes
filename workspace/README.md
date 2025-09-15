#####################
# Welcome to icotes #
#####################

# Disclaimer #
This is an MVP and not yet a beta, so bugs and stability issues are expected.
Some UI elements may be placeholders.
Do not use this for mission-critical workloads.
This software is provided "as is," without warranties or support.
That said, feel free to try it out and share feedback—would love to hear your thoughts. 

# Quick change log
## [1.8.0] source control panel(GIT) and media handler:
This is a feature release that adds Git panel and several media support capabilities
upload and download files, upload with drag and drop file, download with right click on file choose download.
Please note that chat image support is only on the UI, Agents and tools were not updated to support image, 
stay tune for up comming agent update for image and multimodality support.

# Features at a glance #

## Agent Creator ##
This is the default selected agent. It's a custom agent, and the code lives at
`workspace/.icotes/plugins/agent_creator_agent.py`. You can modify any part of it to fit your needs.

The `MODEL_NAME` defaults to `gpt-5-nano`. To use a more capable model, change the `MODEL_NAME`
constant in the agent implementation or configure it via your environment/runtime settings.

## Features ##
Fully working Editor, Terminal and AI agent that can do CRUD operations on the
File system level, Agent can also run terminal commands and edit any files.

# Index #
Both the frontend and backend cores are designed as standalone frameworks, with
middleware/glue code that connects them for flexibility.

## ICUI ##
This is the main frontend framework used for the UI.
It is designed to be flexible and modular. The arrangement of panels can be reconfigured
with a JSON file.

## ICPY ##
This is the Python/FastAPI backend that powers everything behind the scenes.
It is named ICPY with the intent to explore portions in faster frameworks
such as Rust or Go later on.

## Hot reload ##
To add or update an agent:
1) Create `<AgentName>_agent.py` under the `workspace/.icotes/plugins` folder.
2) Register it in `.icotes/agents.json`.
3) The hot-reload system will pick it up automatically, or click the reload button next to the Agent
   selector in the Chat window to force a reload.
You can use your updated agent immediately after reload.