# ICUI-ICPY Integration Design Document

## Overview
This document outlines the strategy for integrating the ICUI frontend with the ICPY backend. The integration will be implemented in phases, with comprehensive testing at each stage to ensure reliability and stability.

## Goals
1. Create a robust connection between ICUI and ICPY
2. Implement systematic testing for individual components
3. Ensure end-to-end functionality matches existing features
4. Maintain backward compatibility during transition
5. Provide clear debugging and monitoring capabilities

## Architecture

### Component Diagram
```
┌─────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│                 │     │                   │     │                 │
│   ICUI Frontend │<--->│  Connection      │<--->│   ICPY Backend  │
│   (React)       │     │  Layer           │     │   (FastAPI)     │
│                 │     │                   │     │                 │
└─────────────────┘     └───────────────────┘     └─────────────────�n```

### Connection Layer
The connection layer will handle:
- WebSocket management
- Message serialization/deserialization
- Reconnection logic
- Error handling and recovery
- Request/response tracking

## Testing Strategy

### Test Directory Structure
```
src/
└── __tests__/ 
    └── integration/
        ├── connection.test.ts      # WebSocket connection tests
        ├── Explorer.test.tsx       # Explorer component integration
        ├── Terminal.test.tsx       # Terminal component integration
        ├── Editor.test.tsx         # Editor component integration
        └── Home.e2e.test.tsx       # Full end-to-end tests
```

## Implementation Phases

This plan is tailored to the existing architecture in `src/components/home.tsx`. The core idea is to replace the local state management (`useState`) for files and the terminal with state synchronized from the `icpy` backend via a central WebSocket connection.

### Phase 1: Establish Backend Connection & Workspace Sync
**Goal**: Replace the initial hardcoded state in `home.tsx` with data fetched from the `icpy` backend.

1.  **Create a WebSocket Service**: Implement a singleton service (`src/services/socketService.ts`) to manage the WebSocket connection, including connection, disconnection, and reconnection logic.

2.  **Integrate with `Layout.tsx`**: The main `Layout` component should use the service to display the real-time `connectionStatus` in the footer.

3.  **Fetch Initial State in `home.tsx`**: Modify the `useEffect` hooks in `home.tsx`.
    *   On initial mount, after establishing a connection, send a `workspace.get_state` request.
    *   The backend will respond with the current file list, open tabs, and active file.
    *   Use this response to populate the `editorFiles` and `activeFileId` states, replacing `defaultFiles`.

#### Test Case (`connection.test.ts`)
```typescript
it('should connect to the backend and fetch initial workspace state', async () => {
  // Render the Home component, which initializes the socket connection
  render(<Home />);
  
  // Assert that the connection status in the footer shows "Connecting..."
  expect(screen.getByText('Connecting...')).toBeInTheDocument();

  // Simulate a successful connection and the backend sending the initial state
  await act(async () => {
    mockSocket.connect();
    mockSocket.receiveMessage({
      type: 'workspace.state',
      payload: { 
        files: [{ id: 'backend-file.js', name: 'backend-file.js', content: 'console.log("hi")' }],
        activeFileId: 'backend-file.js'
      }
    });
  });

  // Assert that the connection status is now "Connected"
  expect(screen.getByText('Connected')).toBeInTheDocument();

  // Assert that the file received from the backend is now visible in the editor/tabs
  expect(screen.getByText('backend-file.js')).toBeInTheDocument();
});
```

### Phase 2: Integrate the File Explorer
**Goal**: Connect the `ICUIExplorerPanel` to the `icpy` filesystem service.

1.  **Fetch File Tree**: When the `ICUIExplorerPanel` mounts, it should request the root directory contents by sending a `filesystem.get_directory_tree` message.

2.  **Update UI from Backend**: The panel should listen for `filesystem.directory_content` messages and update its display accordingly.

3.  **Wire up File Operations**: The `handleFileCreate` function in `home.tsx` should be modified to send a `filesystem.create_file` message to the backend instead of just updating local state. The UI should update only after receiving a confirmation event from the backend.

#### Test Case (`Explorer.test.tsx`)
```typescript
it('should display the file tree and send a create file request on user action', async () => {
  const user = userEvent.setup();
  render(<Home />);
  mockSocket.connect();

  // Simulate backend sending the initial file tree
  act(() => {
    mockSocket.receiveMessage({ 
      type: 'filesystem.directory_content', 
      payload: { files: [{ name: 'existing-file.txt' }] }
    });
  });

  // Assert the initial file is visible
  expect(await screen.findByText('existing-file.txt')).toBeInTheDocument();

  // Simulate user clicking the 'New File' button
  await user.click(screen.getByRole('button', { name: /new file/i }));

  // Assert that a message was sent to the backend to create the file
  expect(mockSocket.sent).toContainEqual(expect.objectContaining({
    type: 'filesystem.create_file',
    payload: { name: expect.stringContaining('untitled') }
  }));
});
```

### Phase 3: Integrate the Terminal
**Goal**: Connect the `ICUIEnhancedTerminalPanel` to the `icpy` terminal service.

1.  **Request PTY Session**: When the terminal panel mounts, it should request a new terminal session by sending a `terminal.create_session` message.

2.  **Two-Way Communication**: 
    *   User input in the terminal UI should be captured and sent to the backend via `terminal.data_in` messages.
    *   The component must listen for `terminal.data_out` messages from the backend and write the received data to the terminal display (e.g., using Xterm.js).

#### Test Case (`Terminal.test.tsx`)
```typescript
it('should request a terminal session and forward I/O', async () => {
  const user = userEvent.setup();
  render(<Home />); // Assumes Home renders the terminal panel
  mockSocket.connect();

  // Assert that a request to create a terminal was sent on mount
  expect(mockSocket.sent).toContainEqual({ type: 'terminal.create_session' });

  // Simulate user typing a command
  await user.type(screen.getByRole('textbox'), 'ls{enter}');

  // Assert that the input was sent to the backend
  expect(mockSocket.sent).toContainEqual({ type: 'terminal.data_in', payload: { data: 'ls\r' } });

  // Simulate the backend sending command output
  act(() => {
    mockSocket.receiveMessage({ type: 'terminal.data_out', payload: { data: 'file1.txt' } });
  });

  // Assert that the output is now visible in the terminal
  expect(await screen.findByText('file1.txt')).toBeInTheDocument();
});
```

### Phase 4: Integrate the Editor
**Goal**: Connect the `ICUIEnhancedEditorPanel` to the backend for file management and code execution.

1.  **Load File Content**: When a user clicks a file in the `ICUIExplorerPanel`, the `handleFileActivate` function should now send a `filesystem.read_file` message. The content will be loaded into the editor upon receiving a `filesystem.file_content` response.

2.  **Save Changes**: The `handleFileChange` and `handleFileSave` callbacks should be updated to send `filesystem.update_file` messages to the backend, replacing the local state updates.

3.  **Backend Code Execution**: The `handleFileRun` function must be completely rewritten. Instead of using `eval()`, it will send a `code.execute` message to the backend with the file's content and language. The results will be displayed in the `Terminal` or an `Output` panel.

#### Test Case (`Editor.test.tsx`)
```typescript
it('should save changes to the backend and run code', async () => {
  const user = userEvent.setup();
  render(<Home />); // Render with a pre-loaded file
  mockSocket.connect();
  
  // Simulate user typing in the editor
  await user.type(screen.getByRole('textbox'), 'console.log("new code");');

  // Simulate user saving the file (e.g., Ctrl+S or clicking a save button)
  await user.click(screen.getByRole('button', { name: /save/i }));

  // Assert that the updated content was sent to the backend
  expect(mockSocket.sent).toContainEqual(expect.objectContaining({
    type: 'filesystem.update_file',
    payload: expect.objectContaining({ content: expect.stringContaining('new code') })
  }));

  // Simulate user clicking the 'Run' button
  await user.click(screen.getByRole('button', { name: /run/i }));

  // Assert a code execution request was sent to the backend
  expect(mockSocket.sent).toContainEqual({ type: 'code.execute', payload: { ... } });
});
```

### Phase 5: End-to-End Integration Testing
**Goal**: Test full user workflows with all components interacting.

#### Test Cases
1. **File Explorer + Editor**
   - Test opening file from explorer in editor
   - Test saving file updates explorer

2. **Terminal + File System**
   - Test terminal commands that affect files
   - Verify explorer updates on file changes

3. **Editor + Terminal**
   - Test running code from editor in terminal
   - Test sending editor selection to terminal

### Phase 4: End-to-End Testing
**Goal**: Test complete user flows

#### Test Scenarios
1. **Project Initialization**
   - Load project
   - Verify all components initialize correctly
   - Check initial state matches project config

2. **Development Workflow**
   - Create new file
   - Edit and save file
   - Run file in terminal
   - Check output

## Test Utilities

#### Mock WebSocket Server
A mock WebSocket server is crucial for isolating frontend components from the real backend during tests. Libraries like `mock-socket` can be used.

```typescript
// src/__tests__/mocks/socket.ts
import { vi } from 'vitest';

// A simplified mock socket for demonstration
export const mockSocket = {
  sent: [],
  send(message) {
    this.sent.push(JSON.parse(message));
  },
  receiveMessage(message) {
    // This would trigger the 'onmessage' event handler in the app
    window.dispatchEvent(new MessageEvent('message', { data: JSON.stringify(message) }));
  },
  clear() {
    this.sent = [];
  }
};

vi.mock('../services/socketService', () => ({
  socket: mockSocket
}));
```

#### Custom Render Function
A custom render function can wrap components with necessary providers (e.g., state management, theme) to simplify test setup.

```typescript
// src/__tests__/test-utils.tsx
import { render } from '@testing-library/react';
import { ThemeProvider } from '../contexts/ThemeContext';
import { StateProvider } from '../contexts/StateContext';

const AllTheProviders = ({ children }) => {
  return (
    <ThemeProvider>
      <StateProvider>{children}</StateProvider>
    </ThemeProvider>
  );
};

const customRender = (ui, options) => 
  render(ui, { wrapper: AllTheProviders, ...options });

// re-export everything
export * from '@testing-library/react';

// override render method
export { customRender as render };
```

## Debugging and Monitoring

### Logging
- Enable verbose logging for connection events
- Log all messages in development mode
- Include message IDs for correlation

### Metrics
- Connection latency
- Message throughput
- Error rates
- Component initialization time

## Error Handling

### Expected Errors
1. **Connection Issues**
   - Network errors
   - Timeouts
   - Authentication failures

2. **Message Errors**
   - Invalid message format
   - Unknown message types
   - Permission denied

### Recovery Strategies
- Automatic reconnection with exponential backoff
- Graceful degradation of features
- User-friendly error messages

## Performance Considerations

### Optimization Targets
- Initial connection time < 500ms
- Message round-trip time < 100ms
- Memory usage under load
- Concurrent connection handling

## Future Enhancements
1. **Progressive Loading**
   - Load components on demand
   - Lazy load large file contents

2. **Offline Support**
   - Cache frequently accessed files
   - Queue operations when offline

3. **Advanced Testing**
   - Visual regression testing
   - Performance benchmarking
   - Load testing

## Rollout Plan
1. **Alpha Testing**
   - Internal team testing
   - Basic functionality verification

2. **Beta Testing**
   - Limited external testers
   - Real-world usage scenarios

3. **Production Rollout**
   - Gradual rollout to users
   - Monitoring and quick response to issues

## Rollback Plan
- Maintain previous version
- Feature flag for new implementation
- Quick rollback procedure
- Data migration if needed
