Environment Summary
Generated on: 2025-08-22

System
- OS/Kernel: Linux icotesdev 6.8.12-13-pve x86_64 (PREEMPT_DYNAMIC)
- Python: 3.12.3

Workspace
- Resolved path: /home/penthoy/icotes/workspace
- Top-level items:
  - .icotes/
  - plugins/
  - README.md
  - test_claude_client.py
  - ticket_replace_string_in_file.md
- Files (max depth 2):
  - ./.icotes/agents.json
  - ./README.md
  - ./plugins/agent_creator_agent.py
  - ./plugins/claude_agent_creator_agent.py
  - ./plugins/example_tool_using_agent.py
  - ./test_claude_client.py
  - ./ticket_replace_string_in_file.md

Plugins (source overview)
- agent_creator_agent.py
  - AGENT_MODEL_ID: gpt-5
  - Metadata (via helpers): name=AgentCreator, version=2.1.1, author=Hot Reload System
  - Fallback metadata if helpers unavailable: version=2.1.0
- claude_agent_creator_agent.py
  - AGENT_MODEL_ID: claude-3-5-sonnet-20241022
  - Metadata: name=ClaudeAgentCreator, version=1.0.0, author=Hot Reload System
- example_tool_using_agent.py
  - AGENT_NAME: ExampleToolUser
  - Version: 1.0.0
  - Demonstrates tool usage for: semantic_search, read_file, create_file, replace_string_in_file, run_in_terminal

Agent Registry (.icotes/agents.json)
- Agents:
  - AgentCreator: enabled=true, displayName="Agent Creator", category=Custom Agents, order=2, icon=🧠
  - PersonalAgent: enabled=false, displayName="Personal Assistant (Tool Demo)", category=Built-in, order=5
  - OpenAIDemoAgent: enabled=true, displayName="OpenAI Demo", category=Built-in, order=1, icon=🤖
  - OpenRouterAgent: enabled=true, displayName="OpenRouter", category=Built-in, order=4, icon=🌐
  - Qwen3CoderAgent: enabled=false, displayName="Qwen3CoderAgent", category=Built-in, order=999, icon=💻
  - ExampleToolUser: enabled=true, displayName="ExampleToolUser", category=Tests, order=999
  - ClaudeAgentCreator: enabled=true, displayName="Claude Agent Creator", category=Custom Agents, order=3, icon=🧠
- Categories:
  - Custom Agents (icon=🛠️, order=2)
  - Tests (icon=💬, order=3)
  - Built-in (icon=🧠, order=1)
- Settings:
  - showCategories=true, showDescriptions=true, defaultAgent=AgentCreator, autoReloadOnChange=true

README highlights
- This is an MVP; expect bugs/instability.
- Agent Creator is customizable in plugins/agent_creator_agent.py.
- Features include a working editor, terminal, and agents with CRUD over the filesystem and terminal execution.
- ICUI (frontend) and ICPY (backend) are designed as modular components.

Environment variables (names only)
- ANTHROPIC_API_KEY
- GIT_ASKPASS
- GOOGLE_API_KEY
- NODE
- OPENAI_API_KEY
- PATH
- VIRTUAL_ENV
- WORKSPACE_ROOT

Notes and observations
- ClaudeAgentCreator specifies model: claude-3-5-sonnet-20241022. If you encounter model_not_found errors, verify Anthropic credentials and model access.
- AgentCreator uses model identifier: gpt-5. Ensure your router or OpenAI configuration maps this to an available model.
- Tools available to agents (as demonstrated): semantic_search, read_file, create_file, replace_string_in_file, run_in_terminal.
