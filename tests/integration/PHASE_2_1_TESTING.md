# Phase 2.1 File Explorer Integration - Manual Testing Guide

## Overview
This guide covers manual testing procedures for the newly implemented backend-connected file explorer in Phase 2.1 of the ICUI-ICPY integration.

## Test Environment Setup

### Prerequisites
1. **Backend Server**: ICPY backend running on `http://192.168.2.195:8000`
2. **Frontend**: Built and served via backend at `http://192.168.2.195:8000`
3. **Integration Route**: Access test interface at `http://192.168.2.195:8000/integration`

### Starting the Test Environment
```bash
# Terminal 1: Start backend server
cd /home/penthoy/icotes/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Build frontend (if needed)
cd /home/penthoy/icotes
npm run build
```

## Test Scenarios

### 1. Basic Connection and Loading

**Test Case**: File Explorer Connection
- **Action**: Navigate to `http://192.168.2.195:8000/integration`
- **Expected**: 
  - Page loads successfully
  - Integration test environment displays
  - Left sidebar shows "Backend Explorer" panel
  - Connection status indicator shows "Connected" (green dot)
- **Verification**: Check that backend explorer panel is visible and connected

**Test Case**: Directory Loading
- **Action**: Observe the file explorer panel after connection
- **Expected**: 
  - Directory contents load automatically
  - Files and folders display with appropriate icons (📁 for folders, 📄 for files)
  - Loading indicator appears briefly during initial load
- **Verification**: Directory structure reflects actual backend filesystem

### 2. File Operations

**Test Case**: Create New File
- **Action**: Click the "📄" button in the explorer header
- **Expected**: 
  - Prompt appears asking for file name
  - Enter filename (e.g., "test-file.txt")
  - File appears in the explorer tree
  - Directory refreshes automatically
- **Verification**: File should be created in backend and visible in explorer

**Test Case**: File Selection
- **Action**: Click on any file in the explorer tree
- **Expected**: 
  - File becomes highlighted/selected
  - Status bar shows "Selected: filename"
  - Console logs file selection (check browser dev tools)
- **Verification**: File selection state updates correctly

**Test Case**: File Deletion
- **Action**: Click the "×" button next to a file (appears on hover)
- **Expected**: 
  - Confirmation dialog appears
  - Click "OK" to confirm deletion
  - File disappears from explorer
  - Directory refreshes automatically
- **Verification**: File should be deleted from backend

### 3. Folder Operations

**Test Case**: Create New Folder
- **Action**: Click the "📁" button in the explorer header
- **Expected**: 
  - Prompt appears asking for folder name
  - Enter folder name (e.g., "test-folder")
  - Folder appears in the explorer tree
  - Directory refreshes automatically
- **Verification**: Folder should be created in backend and visible in explorer

**Test Case**: Folder Navigation
- **Action**: Click on a folder in the explorer tree
- **Expected**: 
  - Folder expands/collapses
  - If expanding for first time, folder contents load
  - Folder icon changes (📁 closed → 📂 open)
- **Verification**: Folder navigation works correctly

### 4. Connection Status and Error Handling

**Test Case**: Connection Status Indicator
- **Action**: Observe the connection status in explorer header and status bar
- **Expected**: 
  - Status shows "connected" when backend is available
  - Green indicator in status bar
  - All buttons enabled when connected
- **Verification**: Connection status accurately reflects backend availability

**Test Case**: Disconnection Handling
- **Action**: Stop the backend server temporarily
- **Expected**: 
  - Connection status changes to disconnected
  - "Not connected to backend" message appears
  - File operation buttons become disabled
  - Error messages appear for failed operations
- **Verification**: UI gracefully handles disconnection

**Test Case**: Error Handling
- **Action**: Try to create a file with invalid name or in read-only location
- **Expected**: 
  - Error message appears in red banner
  - User receives feedback about the failure
  - UI remains functional
- **Verification**: Error states are handled properly

### 5. Integration Test Environment

**Test Case**: Overall Integration
- **Action**: Use the integration test environment holistically
- **Expected**: 
  - File explorer works alongside other integration components
  - File operations reflect in file list
  - Terminal operations work independently
  - Connection status is consistent across components
- **Verification**: All integration components work together seamlessly

**Test Case**: Theme Compatibility
- **Action**: Change theme using the theme selector
- **Expected**: 
  - File explorer adapts to new theme
  - Colors and styling update correctly
  - Functionality remains intact
- **Verification**: Explorer works with all available themes

## Performance Testing

### Load Testing
- **Test**: Load directory with many files
- **Expected**: Directory loads within reasonable time (< 5 seconds)
- **Verification**: Performance remains acceptable with larger directories

### Refresh Testing
- **Test**: Rapid file operations (create, delete multiple files)
- **Expected**: Directory refreshes correctly after each operation
- **Verification**: State remains consistent between frontend and backend

## Troubleshooting

### Common Issues

**Issue**: Explorer shows "No files found" when backend is connected
- **Solution**: Check backend server logs for errors
- **Check**: Verify backend filesystem service is running
- **Debug**: Use browser dev tools to check API calls

**Issue**: File operations fail silently
- **Solution**: Check browser console for JavaScript errors
- **Check**: Verify backend API endpoints are responding
- **Debug**: Check network tab in browser dev tools

**Issue**: Connection status shows disconnected when backend is running
- **Solution**: Verify WebSocket connection is established
- **Check**: Check backend logs for connection errors
- **Debug**: Restart backend server and refresh frontend

## Success Criteria

### Phase 2.1 Complete When:
- ✅ Backend-connected file explorer displays correctly
- ✅ File operations (create, delete, select) work via backend API
- ✅ Folder operations (create, navigate) work via backend API
- ✅ Connection status accurately reflects backend availability
- ✅ Error handling provides appropriate user feedback
- ✅ Integration with existing test environment is seamless
- ✅ Performance is acceptable for typical use cases

## Next Steps

After successful completion of Phase 2.1 testing:
1. **Proceed to Phase 2.2**: Terminal Integration
2. **Document any issues**: Report bugs found during testing
3. **Performance optimization**: If needed based on test results
4. **User feedback**: Collect feedback on explorer usability

## Notes

- All tests should be performed with backend running
- Check browser console for any JavaScript errors
- Verify backend logs for server-side errors
- Test with different file types and names
- Test edge cases (empty directories, special characters, etc.)
