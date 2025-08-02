# Integration Test Manual Testing Guide

## Quick Start

1. **Start the backend server**:
   ```bash
   cd backend
   python main.py
   ```

2. **Start the frontend dev server**:
   ```bash
   npm run dev
   ```

3. **Navigate to the integration test**:
   Open your browser and go to: `http://localhost:8000/integration`

## What You'll See

### Integration Test Environment
The integration test provides a comprehensive testing interface with:

#### Header
- **Connection Status**: Shows if the frontend is connected to the backend
- **Real-time connection indicator** (green = connected, red = disconnected, yellow = connecting)

#### Main Panel (Left Side)
- **File List**: Shows files synchronized from the backend
- **Terminal List**: Shows terminal sessions from the backend
- **Real-time updates** when files or terminals are created/modified

#### Main Panel (Right Side)
- **Integration Status**: Current connection state and counts
- **Theme Control**: Test theme synchronization with backend
- **File Operations**: Buttons to create test files
- **Terminal Operations**: Buttons to create test terminals

#### Footer
- **Backend Status**: Shows workspace info, file count, terminal count
- **Test Controls**: Manual test buttons
  - **Connect/Disconnect**: Toggle backend connection
  - **Create File**: Create test files
  - **Create Terminal**: Create test terminals
  - **Execute Code**: Test code execution

## Testing Scenarios

### 1. Connection Testing
- **Expected**: Auto-connects on load, shows "Connected" status
- **Test**: Click "Disconnect" then "Connect" to test reconnection
- **Verify**: Status changes appropriately, error messages shown if backend is down

### 2. File Operations Testing
- **Create Files**: Click "Create Example File" or "Create Python File"
- **Expected**: Files appear in the file list immediately
- **Verify**: Files are created in the backend workspace

### 3. Terminal Operations Testing
- **Create Terminals**: Click "Create Development Terminal" or "Create Test Terminal"
- **Expected**: Terminals appear in the terminal list
- **Verify**: Terminal sessions are created in the backend

### 4. Theme Synchronization Testing
- **Change Theme**: Use the theme dropdown
- **Expected**: Theme changes immediately and syncs to backend
- **Verify**: Preference is saved to backend workspace

### 5. Backend State Synchronization
- **Real-time Updates**: Changes should be reflected immediately
- **State Persistence**: Refresh the page, state should be restored from backend
- **Error Handling**: Stop the backend, should show error messages

## Expected Behavior

✅ **When Backend is Running**:
- Connection status shows "Connected" (green)
- File and terminal operations work immediately
- Backend status shows workspace information
- Theme changes are synchronized
- Error messages are clear and helpful

❌ **When Backend is Down**:
- Connection status shows "Disconnected" (red)
- Operations are disabled
- Error messages explain the connection issue
- Auto-reconnection attempts are made

## Troubleshooting

### Backend Connection Issues
1. **Check backend is running**: `curl http://localhost:8000/health`
2. **Check WebSocket endpoint**: Should be `ws://localhost:8000/ws/enhanced`
3. **Check console for errors**: Browser developer tools should show connection details

### Frontend Issues
1. **Check imports**: All backend services should be imported correctly
2. **Check types**: TypeScript should compile without errors
3. **Check hooks**: `useBackendState` and `useBackendContext` should work

## Key Features Being Tested

1. **Backend Context Provider**: Application-wide backend access
2. **WebSocket Connection**: Real-time communication with backend
3. **State Synchronization**: Bi-directional state updates
4. **Error Handling**: Graceful error recovery
5. **Connection Recovery**: Auto-reconnection on failure
6. **Type Safety**: All operations are type-safe

## Next Steps

After manual testing confirms everything works:
1. **Phase 2.1**: File Explorer Integration
2. **Phase 2.2**: Terminal Integration  
3. **Phase 2.3**: Editor Integration

## Development Notes

- The integration test is in `tests/integration/integration.tsx`
- Backend services are in `src/services/`
- Backend types are in `src/types/backend-types.ts`
- Context provider is in `src/contexts/BackendContext.tsx`
- State hook is in `src/hooks/useBackendState.ts`

This test environment will serve as the foundation for all future integration work.
