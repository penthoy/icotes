# File Watcher – Step-by-step Debug Plan

Purpose: make the Explorer update immediately when files are created/renamed/deleted from the shell by tracing the full path: OS → watchdog → backend message broker → websocket → frontend service → Explorer refresh.

## What we will instrument

We’ll add compact, clearly-tagged logs at each hop with enough context to correlate events.

Legend for tags we will use in logs:
- [FS] – backend filesystem service (watchdog handlers)
- [WS] – backend websocket API (subscriptions/broadcasts)
- [BE] – frontend backend service (websocket client adapter)
- [EXPL] – frontend Explorer component

For each emitted line we’ll include: event, path(s), workspaceRoot/currentPath where relevant, connection/subscription details, and a short event id.

Event ID format: eid=<epoch_ms mod 100000> to keep logs short but sortable.

---

## End-to-end flow (expected)
1) OS change happens in WORKSPACE_ROOT.
2) [FS] watchdog handler publishes `fs.file_created|fs.file_deleted|fs.file_moved` with payload including file_path/src_path/dest_path.
3) [WS] websocket API receives broker event and broadcasts `type: filesystem_event, event: fs.*` to connections that subscribed (pattern `fs.*`).
4) [BE] frontend EnhancedWebSocketService delivers the message to ICUIBackendService which re-emits `filesystem_event` with normalized `path`.
5) [EXPL] Explorer listens to `filesystem_event`, checks `filePath.startsWith(currentPath)`, and schedules a debounced refresh.

We’ll verify each arrow with logs.

---

## Step-by-step checks

### A) Backend watcher → broker
- Add log (or confirm existing):
  - On create: `[FS] on_created eid=<id> root=<root> path=<file_path> observer_alive=<bool> watched_count=<n>`
  - On modify/delete/move similarly; for move include `src=… dest=…`.
- Add a one-shot “watcher status” log at startup and on demand:
  - `[FS] watcher_started root=<root> recursive=true is_alive=<bool>`
  - Expose a simple `/api/fs/watcher_status` endpoint (optional) returning root, watched_paths, observer state.

Manual test:
- From workspace root: `touch a.txt` → expect an `[FS] on_created ... path=/.../a.txt` within <200ms.

### B) Broker → websocket broadcast
- On subscription: `[WS] subscribed conn=<id> topics=[…]` (already present)
- On broadcast: `[WS] fs_broadcast eid=<id> event=<fs.file_created> conns=<count> sample_conn=<id> payload_keys=[...]`
- When matching subscriptions: `[WS] match subscription=<topic> pattern=fs.*` (optional at debug level)

Manual test:
- After `touch a.txt`, expect a `[WS] fs_broadcast ...` line.

### C) Frontend socket receive → ICUIBackendService emit
- In EnhancedWebSocketService handler (already logs basic info) and in ICUIBackendService `handleWebSocketMessage`:
  - `[BE] fs_msg eid=<id> event=<fs.file_created> path=<normalized_path>`
- Normalize path from `file_path|path|dest_path|src_path`.

Manual test:
- Browser devtools console should show the `[BE] fs_msg ...` line on file create.

### D) Explorer subscription → refresh
- When Explorer mounts and subscribes:
  - `[EXPL] subscribe eid=<id> path=<currentPath>` then backend reply `[BE] subscribed topics=…` should appear.
- On event receipt:
  - `[EXPL] fs_evt eid=<id> event=<fs.file_created> filePath=<p> currentPath=<cp> match=<true|false>`
- When scheduling refresh:
  - `[EXPL] refresh_scheduled in=300ms reason=fs.file_created`
- On refresh execution:
  - `[EXPL] refresh eid=<id> path=<cp> hidden=<bool>` and number of nodes returned.

Manual test:
- Create, delete, move files and confirm the above sequence appears and tree updates.

---

## Test matrix (run in order and capture logs)

1) Create a file at workspace root
   - `touch <root>/alpha.txt`
2) Create inside a new folder
   - `mkdir -p <root>/dir1; touch <root>/dir1/inner.txt`
3) Move/rename
   - `mv <root>/alpha.txt <root>/alpha-renamed.txt`
4) Delete
   - `rm <root>/alpha-renamed.txt`
5) Hidden file
   - `touch <root>/.hidden_test`
6) Deep subfolder
   - `mkdir -p <root>/a/b/c; touch <root>/a/b/c/deep.txt`
7) Two browser tabs
   - Confirm both tabs receive `[EXPL] fs_evt` and refresh.

For each, note whether Explorer updated without manual refresh.

---

## How we’ll enable/disable debug

- Backend: toggle via env `LOG_LEVEL=DEBUG` (and we’ll gate new debug lines behind logger.debug). Optionally an `ICPY_FS_DEBUG=1` env to force extra watcher status output.
- Frontend: toggle via localStorage key `ICUI_DEBUG_FS=1` (Explorer and backend service will check this and console.log only when set).

We’ll implement these toggles alongside the logs to keep noise low in normal use.

---

## Artifacts you can share after each test

- Backend console snippets showing `[FS]` and `[WS]` lines for a given action.
- Browser console snippets showing `[BE]` and `[EXPL]` lines.
- Whether the Explorer view changed without manual refresh.

This will pinpoint the exact hop that fails (no [FS] → watcher; no [WS] → broker/ws; no [BE] → frontend socket; no [EXPL] → UI refresh).

---

## Next implementation steps (after approval)

- Add the precise logs above:
  - filesystem_service: per-event logs + watcher_started + optional `/api/fs/watcher_status`.
  - websocket_api: fs_broadcast summary.
  - ICUI backend service: `[BE] fs_msg` + gate behind `ICUI_DEBUG_FS`.
  - Explorer: `[EXPL] subscribe/fs_evt/refresh_*` + gate behind `ICUI_DEBUG_FS`.
- Add the `ICUI_DEBUG_FS` check (localStorage) and `ICPY_FS_DEBUG` env check.
- Provide a short “Try it” guide with copyable commands and the expected log sequence.

Once these are in, we’ll iterate with your manual results to close the gap.
