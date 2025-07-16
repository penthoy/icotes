# ICPI Backend Rewrite Plan - Modular Service-Based Architecture

## 1. Overview & Mission

This document outlines the step-by-step plan for rewriting the icotes backend into a modular, service-based architecture. The mission is to create a backend that acts as a **single source of truth** for the frontend, is highly performant, and is built for extensibility.

This plan is inspired by the modularity of `icui_rewrite.md` and the architectural principles of `agent-backend-guide.md` and `backend-code-server.md`.

## 2. Core Principles

*   **Modular Services**: Each core functionality (e.g., File System, Terminal, Code Execution) will be a separate, independent service.
*   **Event-Driven Communication**: Services will communicate asynchronously via a central message broker, promoting loose coupling and scalability.
*   **Single WebSocket Connection**: The frontend will establish a single, persistent WebSocket connection for all real-time communication.
*   **Unified API Layer**: A single API Gateway will expose all functionality through a consistent interface, accessible by the frontend, CLIs, or other AI tools.
*   **Standardized Protocol**: All communication will use a defined JSON-RPC 2.0 protocol over WebSocket.
*   **Phased Rollout with Testing**: Each phase will be developed and tested independently to ensure stability.

## 3. High-Level Architecture

```mermaid
graph TD
    subgraph Browser
        A[Frontend UI]
    end

    subgraph "Backend (icpi)"
        B[API Gateway <br/> (FastAPI)]
        C[Message Broker <br/> (In-Memory asyncio.Queue)]

        subgraph "Core Services"
            D[Workspace Service]
            E[File System Service]
            F[Terminal Service]
            G[Code Execution Service]
            H[Agent Service]
        end
    end

    A -- "HTTP/WebSocket (JSON-RPC)" --> B
    B -- "Events" --> C
    C -- "Events" --> D
    C -- "Events" --> E
    C -- "Events" --> F
    C -- "Events" --> G
    C -- "Events" --> H

    D -- "Events" --> C
    E -- "Events" --> C
    F -- "Events" --> C
    G -- "Events" --> C
    H -- "Events" --> C
```

## 4. Implementation Phases

---

### Phase 1: Core Foundation & API Gateway

**Goal**: Establish the fundamental components of the new architecture: the API Gateway and the Message Broker.

#### **Step 1.1: Setup Initial Project Structure**
- Create a new directory `backend_icpi` to house the new backend.
- Initialize a new FastAPI project within it.
- Create a `requirements.txt` with `fastapi`, `uvicorn`, `websockets`.

#### **Step 1.2: Implement API Gateway**
- Create `backend_icpi/main.py`.
- Implement a basic FastAPI application.
- Add a single WebSocket endpoint at `/ws` that establishes a persistent connection.

#### **Step 1.3: Implement In-Memory Message Broker**
- Create `backend_icpi/message_broker.py`.
- Implement a simple message broker using `asyncio.Queue`.
- It should support `publish` and `subscribe` methods.
- The API Gateway will forward all incoming WebSocket messages to this broker.

#### **Step 1.4: Integration Test**
- Create `tests/integration/icpi/test_phase_1.py`.
- Write a test that connects a WebSocket client to the `/ws` endpoint.
- Send a sample JSON-RPC message.
- Assert that the message is received by the message broker.

---

### Phase 2: Workspace Service

**Goal**: Create the service responsible for managing the overall state of the IDE workspace.

#### **Step 2.1: Implement Workspace Service**
- Create `backend_icpi/services/workspace_service.py`.
- This service will subscribe to events like `file.opened`, `file.closed`, `terminal.created`.
- It will maintain a state dictionary representing open files, active terminals, etc.
- When its state changes, it will publish a `workspace.updated` event with the new state.

#### **Step 2.2: Define Initial State Events**
- Define the structure for `file.opened` and `terminal.created` events.
- The API gateway will initially be responsible for publishing these when it receives corresponding requests.

#### **Step 2.3: Integration Test**
- Create `tests/integration/icpi/test_phase_2.py`.
- Write a test to send a `file.opened` event via the WebSocket.
- The test will subscribe to the message broker and assert that a `workspace.updated` event is published with the correct state.

---

### Phase 3: File System Service

**Goal**: Abstract all file system operations into a dedicated service.

#### **Step 3.1: Implement File System Service**
- Create `backend_icpi/services/fs_service.py`.
- This service will handle all interactions with the file system.
- It will subscribe to methods like `fs.read_file`, `fs.write_file`, `fs.list_directory`.
- It will publish events like `fs.file_content`, `fs.directory_listing`.

#### **Step 3.2: Implement File Watcher**
- Integrate a file watcher (e.g., `watchdog`) into the FS Service.
- When a file is changed, created, or deleted on disk, the service will publish a `fs.file_changed` event.
- This enables real-time updates in the frontend if a file is modified externally.

#### **Step 3.3: Integration Test**
- Create `tests/integration/icpi/test_phase_3.py`.
- **Test 1**: Send an `fs.list_directory` request and assert that the correct directory listing is returned.
- **Test 2**: Create a temporary file, and assert that the file watcher detects it and publishes an `fs.file_changed` event.

---

### Phase 4: Terminal Service

**Goal**: Refactor terminal management into its own service.

#### **Step 4.1: Implement Terminal Service**
- Create `backend_icpi/services/terminal_service.py`.
- This service will manage the lifecycle of all pseudoterminals (PTYs).
- It will subscribe to `terminal.create`, `terminal.data_in`, `terminal.resize`.
- It will publish `terminal.data_out` events tagged with a unique terminal ID.

#### **Step 4.2: Migrate Existing PTY Logic**
- Adapt the PTY management logic from the old `backend/terminal.py` into the new service.
- Ensure it runs in its own asyncio task.

#### **Step 4.3: Integration Test**
- Create `tests/integration/icpi/test_phase_4.py`.
- Send a `terminal.create` request.
- Send `terminal.data_in` with a simple command like `ls`.
- Assert that the service publishes `terminal.data_out` with the expected output.

---

### Phase 5: Agent & CLI Service

**Goal**: Create a service that allows AI agents and command-line tools to interact with the IDE.

#### **Step 5.1: Implement Agent Service**
- Create `backend_icpi/services/agent_service.py`.
- This service will expose high-level actions that can be called by external tools.
- It will subscribe to events like `agent.open_file`, `agent.run_command`.
- It will translate these high-level commands into the appropriate low-level service events (e.g., `agent.open_file` -> `file.open`).

#### **Step 5.2: Create CLI Entrypoint**
- Create a simple Python script `icotes_cli.py`.
- This script will use a library like `click` or `argparse`.
- It will connect to the backend's WebSocket and send JSON-RPC messages corresponding to the agent service.
- Example: `python icotes_cli.py open-file my_app/main.py`.

#### **Step 5.3: Integration Test**
- Create `tests/integration/icpi/test_phase_5.py`.
- Use Python's `subprocess` to run the `icotes_cli.py` script.
- Assert that the correct events are published on the message broker. For example, running the CLI to open a file should result in a `workspace.updated` event showing the file as open.

## 5. File Structure
```
backend_icpi/
├── main.py                 # FastAPI Gateway
├── message_broker.py       # Asyncio Message Broker
├── services/
│   ├── __init__.py
│   ├── workspace_service.py
│   ├── fs_service.py
│   ├── terminal_service.py
│   └── agent_service.py
├── requirements.txt
└── tests/
    └── integration/
        └── icpi/
            ├── test_phase_1.py
            ├── test_phase_2.py
            ├── test_phase_3.py
            ├── test_phase_4.py
            └── test_phase_5.py

icotes_cli.py # At the root of the project
```

## 6. Migration & Rollout Strategy

1.  **Develop in Parallel**: The entire `backend_icpi` will be developed alongside the existing `backend` without interference.
2.  **Feature Flag in Frontend**: A feature flag will be added to the frontend to switch between the old backend and the new `icpi` backend.
3.  **Incremental Testing**: As each phase of `icpi` is completed, it can be tested with the frontend by enabling the feature flag.
4.  **Full Migration**: Once all phases are complete and stable, the old `backend` directory can be archived and removed. 