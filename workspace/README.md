#####################
# Welcome to icotes #
#####################

# Disclaimer
This is currently only just an MVP and hardly considered beta, 
so bugs and stability issues are to be expected. 
some UI elements might even be place holders.
so I wouldn't advice to build your mission critical software with it
This is provided as-is, is you used this to broke some things, you're entirely on your own.
That said feel free to try it out and tell me what you think, 
would loved to hear your feedback. 

# Features at a glance.

## Agent Creator:
You'll see This is the agent selected by default, 
it is a custom agent meaning you can access the code of this agent directly 
under the workspace/plugins folder under agent_creator_agent.py 
and you can change and update any part of this agent to fit your need.
First thing you can try is to change MODEL_NAME by default using gpt-5-nano but if you
want higher power, you know what to do :)

## Features:
Fully working Editor, Terminal and AI agent that can do CRUD operations on the
File system level, Agent can also run terminal commands and edit any files.

# index:
both the frontend and backend core are designed to be a standalone framework with
middleware/glue code that connect them together, in order to be very flexible.

## ICUI:
This is the main frontend frame work that's used for all the UI you see,
it is designed to be flexible and modular. the arrangement of all the panels can be reconfigured
with a json file.

## ICPY:
This is the python/fastapi backend that powers everything going on behind the scene.
it is named ICPY as I have some plans to make part of the backend using faster frameworks
in rust or go later on.

## Hot reload:
When you create <Agent_name>_agent.py under plugins folder, and after editing the .icotes/agents.json to register it.
The hot reload system can pick it up automatically, or press the reload button next to the Agent selector on the Chat window
which will force it to reload. and you can use your updated/created agent right away.