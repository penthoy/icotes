Of course. Here is a design document for the backend architecture.

---

### **Design Doc: Project "Helios" Backend Architecture**

#### 1. Mission

To create a backend for a web-based IDE that acts as a **single source of truth** for the frontend. The architecture will be modular, extremely fast, and communication-centric. It will be initially implemented in FastAPI and designed for a seamless, piece-by-piece migration to a higher-performance language like Rust or Go.

#### 2. Core Principles

*   **Single Connection:** The frontend establishes a single, persistent WebSocket connection to the backend upon loading. All subsequent communication flows through this channel. This minimizes HTTP overhead and simplifies state management.
*   **Event-Driven:** The backend services are decoupled and communicate internally via an event bus. A service doesn't call another service directly; it emits an event, and other services react to it.
*   **Centralized State:** A dedicated "Workspace" service holds the "ground truth" of the application state (e.g., which files are open, unsaved changes). The frontend's state is a mirror of this.
*   **Standardized Protocol:** All communication, both external (client-server) and internal (inter-service), uses a defined JSON-RPC protocol.

#### 3. High-Level Architecture



#### 4. Component Breakdown

**a. API Gateway (FastAPI)**

*   **Role:** The single public-facing entry point for the entire application.
*   **Responsibilities:**
    1.  Serve the initial Vite-built HTML, JS, and CSS assets.
    2.  Handle user authentication and session management.
    3.  Accept a single WebSocket upgrade request at `/ws`.
    4.  Act as the translator between the external WebSocket and the internal Message Broker. It forwards incoming messages to the broker and pushes outgoing messages to the client.

**b. The Message Broker (The "Single Source of Truth")**

*   **Role:** The central nervous system of the backend. It decouples all services.
*   **How it works:**
    *   Services subscribe to specific event types (e.g., `terminal:keystroke`, `file:save`).
    *   When a message comes from the frontend, the Gateway puts it on the bus. The appropriate service picks it up.
    *   When a service needs to send data or notify of a change, it publishes an event to the bus. The Gateway (and any other interested services) receives it.
*   **Initial Tech (Python):** A simple in-memory `asyncio.Queue`. It's incredibly fast and requires no external dependencies.
*   **Future Tech (Rust/Go):** Can be swapped for a more robust system like Redis Pub/Sub or NATS if you need to scale to multiple machines, but the principle remains the same.

**c. Core Services (Modular, Independent Tasks)**

These run as independent, concurrent `asyncio` tasks, all connected to the Message Broker.

*   **Workspace Service:**
    *   The "brain." It maintains the high-level state.
    *   **Listens for:** `file:open`, `file:close`, `project:load`.
    *   **Publishes:** `state:updated` events containing the latest tree of open files, etc.
    *   The frontend listens to `state:updated` to render its file tabs and explorer.

*   **File System (FS) Service:**
    *   Handles all disk operations. It's the only service that touches the disk.
    *   **Listens for:** `fs:read_file`, `fs:write_file`, `fs:list_directory`.
    *   **Publishes:** `fs:file_content` (in response to a read), `fs:directory_content`, and most importantly, `file:changed_on_disk` if it detects an external change (via `watchdog` or similar).

*   **Terminal Service:**
    *   Manages all pseudoterminal (PTY) lifecycle.
    *   **Listens for:** `terminal:create`, `terminal:data_in` (keystrokes), `terminal:resize`.
    *   **Publishes:** `terminal:data_out` (shell output). Each message is tagged with a unique terminal ID.

#### 5. Communication Protocol: JSON-RPC over WebSocket

Every message is a JSON object with a defined structure. This enforces clarity.

**Request (from Frontend to Backend):**

```json
{
  "jsonrpc": "2.0",
  "id": "request-id-123", // Unique ID to match response
  "method": "fs:read_file",
  "params": {
    "path": "/home/user/app/main.py"
  }
}```

**Response (from Backend to Frontend):**

```json
{
  "jsonrpc": "2.0",
  "id": "request-id-123", // Matches the request ID
  "result": {
    "content": "import os\n\nprint('hello world')"
  }
}
```

**Notification / Event (from Backend to Frontend):**

```json
{
  "jsonrpc": "2.0",
  "method": "terminal:data_out", // No "id" means it's a one-way event
  "params": {
    "terminalId": "term-1",
    "data": "user@hostname:~$ "
  }
}
```

#### 6. Migration Path to Rust/Go(for future)

This architecture makes migration straightforward and low-risk.

1.  **Pick a Service:** Choose a bottleneck to rewrite first, like the FS Service.
2.  **Rewrite in Rust:** Create a new, standalone Rust binary for the FS Service.
3.  **Connect to the Broker:** The key is that the new Rust service connects to the *same message broker* (e.g., Redis Pub/Sub) and speaks the *exact same JSON-RPC protocol*. It subscribes to `fs:read_file` and publishes `fs:file_content`, just like the Python version did.
4.  **Swap It Out:** Turn off the Python FS service and turn on the Rust one.

No other service, and none of the frontend code, needs to be changed. You can migrate the backend piece by piece without a "big bang" rewrite.